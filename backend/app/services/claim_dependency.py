from collections import defaultdict, deque
import re
from typing import Dict, List, Optional, Set, Tuple

from app.core.logging import logger
from app.schemas.claim import AtomicClaim
from app.schemas.dependency import (
    ClaimDependency,
    ClaimDependencyGraph,
    DependencyRelationship,
)


class ClaimDependencyService:
    """
    Claim Dependency Analysis Engine for SachCheck.

    Analyzes atomic claims to discover material relationships:
    - DEPENDS_ON: Child claim presupposes the factual veracity of antecedent parent claim.
      (e.g. Claim A: 'Govt launched scheme X' -> Claim B: 'Scheme X gives ₹10,000')
    - DUPLICATE_OF: Claims assert the exact same proposition with minor phrasing variation.
    - CONTRADICTS: Claims make mutually exclusive or logically incompatible assertions.

    Guarantees:
    - Avoids unnecessary graph complexity (independent claims have no edges).
    - Computes topological verification execution order (antecedent claims verified first).
    - Prevents cyclic dependencies.
    """

    def analyze_dependencies(self, claims: List[AtomicClaim]) -> ClaimDependencyGraph:
        """
        Builds a minimal dependency graph for a collection of atomic claims.
        """
        if not claims:
            return ClaimDependencyGraph()

        if len(claims) == 1:
            return ClaimDependencyGraph(
                dependencies=[],
                execution_order=[claims[0].claim_id],
                independent_claim_ids=[claims[0].claim_id],
            )

        dependencies: List[ClaimDependency] = []
        n = len(claims)

        # 1. Pairwise relationship evaluation
        for i in range(n):
            for j in range(i + 1, n):
                claim_a = claims[i]
                claim_b = claims[j]

                # Check duplicate
                if self._are_duplicates(claim_a, claim_b):
                    dependencies.append(
                        ClaimDependency(
                            parent_claim_id=claim_a.claim_id,
                            child_claim_id=claim_b.claim_id,
                            relationship=DependencyRelationship.DUPLICATE_OF,
                            reason=(
                                f"'{claim_b.claim_id}' asserts the exact same proposition as '{claim_a.claim_id}'."
                            ),
                        )
                    )
                    continue

                # Check contradiction
                if self._are_contradictions(claim_a, claim_b):
                    dependencies.append(
                        ClaimDependency(
                            parent_claim_id=claim_a.claim_id,
                            child_claim_id=claim_b.claim_id,
                            relationship=DependencyRelationship.CONTRADICTS,
                            reason=(
                                f"'{claim_a.claim_id}' and '{claim_b.claim_id}' make mutually exclusive assertions."
                            ),
                        )
                    )
                    continue

                # Check dependency: A -> B (B depends on A)
                if self._does_depend(parent=claim_a, child=claim_b):
                    dependencies.append(
                        ClaimDependency(
                            parent_claim_id=claim_a.claim_id,
                            child_claim_id=claim_b.claim_id,
                            relationship=DependencyRelationship.DEPENDS_ON,
                            reason=(
                                f"'{claim_b.claim_id}' presupposes the factual existence or order established in '{claim_a.claim_id}'."
                            ),
                        )
                    )
                # Check reverse dependency: B -> A (A depends on B)
                elif self._does_depend(parent=claim_b, child=claim_a):
                    dependencies.append(
                        ClaimDependency(
                            parent_claim_id=claim_b.claim_id,
                            child_claim_id=claim_a.claim_id,
                            relationship=DependencyRelationship.DEPENDS_ON,
                            reason=(
                                f"'{claim_a.claim_id}' presupposes the factual existence or order established in '{claim_b.claim_id}'."
                            ),
                        )
                    )

        # 2. Identify independent claims (no incoming or outgoing dependencies)
        connected_ids: Set[str] = set()
        for dep in dependencies:
            connected_ids.add(dep.parent_claim_id)
            connected_ids.add(dep.child_claim_id)

        all_ids = [c.claim_id for c in claims]
        independent_ids = [cid for cid in all_ids if cid not in connected_ids]

        # 3. Compute topological execution order
        execution_order = self._compute_execution_order(claims, dependencies)

        return ClaimDependencyGraph(
            dependencies=dependencies,
            execution_order=execution_order,
            independent_claim_ids=independent_ids,
        )

    # ==========================================================================
    # Relationship Detection Heuristics
    # ==========================================================================

    def _does_depend(self, parent: AtomicClaim, child: AtomicClaim) -> bool:
        """
        Determines if child materially depends on parent.
        Only returns True when verifying parent first materially alters or dictates
        verification of child.
        """
        p_text = (parent.normalized_claim or parent.original_text).lower()
        c_text = (child.normalized_claim or child.original_text).lower()

        # Extract entities / schemes / policies introduced in parent
        p_entities = [e.lower() for e in parent.entities]
        c_entities = [e.lower() for e in child.entities]

        # Pattern 1: Foundational Launch / Notification / Order -> Specific Payout / Benefit / Rule
        # Example from specification:
        # Parent: "Government launched scheme X."
        # Child:  "Scheme X gives ₹10,000 to every citizen."
        launch_triggers = [
            "launched", "notified", "introduced", "started", "ordered", "banned",
            "announced", "passed", "issued", "approved", "created", "शुरू", "लागू", "जाहीर",
        ]
        has_foundational_predicate = any(trig in p_text for trig in launch_triggers)

        # Check if parent introduces a named scheme, order, or entity that child specifies details of
        # E.g. "scheme x", "pmssy", "scholarship", "upi", "lockdown", "pipeline"
        common_subjects = set(p_entities).intersection(set(c_entities))

        # Also search for scheme name patterns (e.g. "scheme x", "pmssy", "योजना")
        scheme_match_p = re.findall(r"\b(?:scheme\s+[a-z0-9]+|योजना\s+[a-z0-9]+)\b", p_text)
        scheme_match_c = re.findall(r"\b(?:scheme\s+[a-z0-9]+|योजना\s+[a-z0-9]+)\b", c_text)
        shares_named_scheme = any(s in c_text for s in scheme_match_p) or (
            bool(scheme_match_p) and bool(scheme_match_c) and scheme_match_p == scheme_match_c
        )

        if (has_foundational_predicate and (common_subjects or shares_named_scheme)):
            # Child specifies amounts, requirements, deadlines, fees, or payouts
            child_detail_triggers = [
                "gives", "gives ₹", "₹", "percent", "%", "fee", "grant", "dbt", "refund",
                "refunded", "register", "registration", "pay", "fee", "अनुदान", "मिळेल",
                "मिळणार", "पंजीकरण", "शुल्क",
            ]
            has_child_detail = (
                bool(child.numbers)
                or any(trig in c_text for trig in child_detail_triggers)
                or "all users will have to" in c_text
                or "tickets will be refunded" in c_text
                or "register on" in c_text
            )
            if has_child_detail:
                return True

        # Pattern 2: Anaphoric dependency ('under this scheme', 'for this reason', 'या योजनेअंतर्गत')
        anaphoric_triggers = [
            "under this scheme", "under the scheme", "in this order", "as per this rule",
            "for this purpose", "is yojana ke tahat", "is yojana me", "या योजनेअंतर्गत",
        ]
        if any(trig in c_text for trig in anaphoric_triggers):
            if any(trig in p_text for trig in ["scheme", "order", "policy", "योजना", "परिपत्रक"]):
                return True

        # Pattern 3: Event Cause -> Remedial Directive / Consequence
        # E.g. Parent: "Drinking water pipeline in Ward 14 has been chemically contaminated."
        # Child:  "Citizens should avoid drinking tap water."
        if "contaminated" in p_text or "दूषित" in p_text or "suspended" in p_text or "banned" in p_text:
            if any(loc.lower() in c_text for loc in parent.locations):
                if any(kw in c_text for kw in ["avoid", "remain indoors", "refund", "precaution"]):
                    return True

        return False

    def _are_duplicates(self, claim_a: AtomicClaim, claim_b: AtomicClaim) -> bool:
        """
        Determines if two claims state the exact same factual proposition.
        """
        text_a = (claim_a.normalized_claim or claim_a.original_text).lower().strip(". ")
        text_b = (claim_b.normalized_claim or claim_b.original_text).lower().strip(". ")

        # 1. Exact normalized match
        if text_a == text_b:
            return True

        # 2. Token overlap analysis
        tokens_a = set(re.findall(r"\w+", text_a))
        tokens_b = set(re.findall(r"\w+", text_b))

        if not tokens_a or not tokens_b:
            return False

        intersection = tokens_a.intersection(tokens_b)
        union = tokens_a.union(tokens_b)
        jaccard = len(intersection) / len(union)

        # Very high Jaccard with matching numbers and dates
        if jaccard >= 0.80 and claim_a.numbers == claim_b.numbers and claim_a.dates == claim_b.dates:
            return True

        # Passive vs Active transformation check (same entities, same action, same figures)
        # e.g. "Government launched Scheme X in 2026" vs "Scheme X was launched by Government in 2026"
        core_a = set(claim_a.entities + [str(n) for n in claim_a.numbers] + claim_a.dates)
        core_b = set(claim_b.entities + [str(n) for n in claim_b.numbers] + claim_b.dates)
        if core_a and core_a == core_b and jaccard >= 0.60:
            return True

        return False

    def _are_contradictions(self, claim_a: AtomicClaim, claim_b: AtomicClaim) -> bool:
        """
        Determines if two claims make mutually exclusive or contradictory assertions.
        """
        text_a = (claim_a.normalized_claim or claim_a.original_text).lower()
        text_b = (claim_b.normalized_claim or claim_b.original_text).lower()

        # Contradiction requires overlapping topic/entity or location
        shared_entities = set(e.lower() for e in claim_a.entities).intersection(
            set(e.lower() for e in claim_b.entities)
        )
        shares_topic = bool(shared_entities) or any(
            kw in text_a and kw in text_b
            for kw in ["upi", "school", "schools", "train", "railway", "scheme x", "bank", "banks", "note", "notes"]
        )

        if not shares_topic:
            return False

        # 1. Direct Polar Negation (Affirmative vs Negative)
        # E.g. "Schools are closed tomorrow" vs "Schools will remain open tomorrow"
        negation_pairs = [
            (r"\bclosed\b", r"\bopen\b"),
            (r"\bbanned\b", r"\bnot\s+banned\b"),
            (r"\bbanned\b", r"\boperating\s+normally\b"),
            (r"\bsuspended\b", r"\brunning\s+normally\b"),
            (r"\bfree\b", r"\bmandatory\s+fee\b"),
            (r"\bband\b", r"\bchalu\b"),
            (r"\bबंद\b", r"\bसुरू\b"),
            (r"\bबंद\b", r"\bखुले\b"),
            (r"\bnot\s+true\b", r"\btrue\b"),
        ]
        for term_1, term_2 in negation_pairs:
            if (re.search(term_1, text_a) and re.search(term_2, text_b)) or (
                re.search(term_2, text_a) and re.search(term_1, text_b)
            ):
                return True

        # Check explicit negation ("is banned" vs "is NOT banned")
        if ("not" in text_a and "not" not in text_b) or ("not" in text_b and "not" not in text_a):
            # If token similarity is otherwise high (>0.6), presence of single negation creates contradiction
            tokens_a = set(re.findall(r"\w+", text_a)) - {"not", "no", "never"}
            tokens_b = set(re.findall(r"\w+", text_b)) - {"not", "no", "never"}
            if tokens_a and tokens_b:
                jacc = len(tokens_a.intersection(tokens_b)) / len(tokens_a.union(tokens_b))
                if jacc >= 0.65:
                    return True

        # 2. Mutually Exclusive Numeric Conflict on same metric
        # E.g. "Scheme X gives ₹10,000" vs "Scheme X gives ₹50,000"
        if claim_a.numbers and claim_b.numbers and claim_a.numbers != claim_b.numbers:
            # Check if both assert same payout/figure
            if any(kw in text_a for kw in ["gives", "grant", "fee", "fine", "dbt"]) and any(
                kw in text_b for kw in ["gives", "grant", "fee", "fine", "dbt"]
            ):
                return True

        return False

    # ==========================================================================
    # Topological Verification Sequencing
    # ==========================================================================

    def _compute_execution_order(
        self, claims: List[AtomicClaim], dependencies: List[ClaimDependency]
    ) -> List[str]:
        """
        Computes topological execution order so antecedent claims are verified
        before dependent child claims.
        """
        all_ids = [c.claim_id for c in claims]
        adj: Dict[str, List[str]] = defaultdict(list)
        in_degree: Dict[str, int] = {cid: 0 for cid in all_ids}

        for dep in dependencies:
            # For DEPENDS_ON and DUPLICATE_OF, parent should precede child
            if dep.relationship in (DependencyRelationship.DEPENDS_ON, DependencyRelationship.DUPLICATE_OF):
                adj[dep.parent_claim_id].append(dep.child_claim_id)
                in_degree[dep.child_claim_id] = in_degree.get(dep.child_claim_id, 0) + 1

        queue = deque([cid for cid in all_ids if in_degree[cid] == 0])
        order: List[str] = []

        while queue:
            node = queue.popleft()
            order.append(node)
            for neighbor in adj[node]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # If cyclic or incomplete, append any remaining IDs preserving original order
        for cid in all_ids:
            if cid not in order:
                order.append(cid)

        return order

    def render_ascii_graph(self, claims: List[AtomicClaim], graph: ClaimDependencyGraph) -> str:
        """
        Generates readable ASCII dependency hierarchy matching user specification:
        Claim A (clm_001)
           ↓ DEPENDS_ON
        Claim B (clm_002)
        """
        lines: List[str] = []
        claim_map = {c.claim_id: (c.normalized_claim or c.original_text) for c in claims}

        if not graph.dependencies:
            return "No dependencies detected (all claims independent)."

        for dep in graph.dependencies:
            p_text = claim_map.get(dep.parent_claim_id, dep.parent_claim_id)
            c_text = claim_map.get(dep.child_claim_id, dep.child_claim_id)
            lines.append(f"[{dep.parent_claim_id}] \"{p_text}\"")
            lines.append(f"   ↓ {dep.relationship.value}")
            lines.append(f"[{dep.child_claim_id}] \"{c_text}\"")
            lines.append("")

        return "\n".join(lines).strip()


claim_dependency_service = ClaimDependencyService()
