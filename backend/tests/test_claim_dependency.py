import pytest
import httpx

from app.main import app
from app.schemas.claim import AtomicClaim
from app.schemas.dependency import (
    ClaimDependency,
    ClaimDependencyGraph,
    DependencyRelationship,
)
from app.services.claim_dependency import (
    ClaimDependencyService,
    claim_dependency_service,
)
from app.services.claim_extractor import claim_extractor_service


# ==============================================================================
# 1. Specification Example: Dependent Claims
# ==============================================================================

def test_specification_example_dependent_claims():
    """
    Verifies the user's specification example:
    Claim A: "Government launched scheme X."
    Claim B: "Scheme X gives ₹10,000 to every citizen."
    Claim B depends on Claim A:
    Claim A
       ↓
    Claim B
    """
    claim_a = AtomicClaim(
        claim_id="clm_001",
        original_text="Government launched scheme X.",
        text="Government launched scheme X.",
        normalized_claim="Government launched scheme X.",
        entities=["scheme x"],
        numbers=[],
        dates=[],
        locations=[],
        claim_type="policy",
        check_worthiness=True,
    )
    claim_b = AtomicClaim(
        claim_id="clm_002",
        original_text="Scheme X gives ₹10,000 to every citizen.",
        text="Scheme X gives ₹10,000 to every citizen.",
        normalized_claim="Scheme X gives ₹10,000 to every citizen.",
        entities=["scheme x"],
        numbers=[10000],
        dates=[],
        locations=[],
        claim_type="financial",
        check_worthiness=True,
    )

    graph = claim_dependency_service.analyze_dependencies([claim_a, claim_b])

    # Exactly 1 material dependency
    assert len(graph.dependencies) == 1
    dep = graph.dependencies[0]
    assert dep.parent_claim_id == "clm_001"
    assert dep.child_claim_id == "clm_002"
    assert dep.relationship == DependencyRelationship.DEPENDS_ON

    # Execution order must verify Claim A before Claim B
    assert graph.execution_order == ["clm_001", "clm_002"]

    # ASCII rendering matches specification
    ascii_tree = claim_dependency_service.render_ascii_graph([claim_a, claim_b], graph)
    assert "[clm_001]" in ascii_tree
    assert "↓ DEPENDS_ON" in ascii_tree
    assert "[clm_002]" in ascii_tree


# ==============================================================================
# 2. Independent Claims (No unnecessary graph complexity)
# ==============================================================================

def test_independent_claims_no_unnecessary_complexity():
    """
    Verifies that unrelated, independent claims have no edges created between them,
    strictly respecting: 'Do not create unnecessary graph complexity.'
    """
    claim_1 = AtomicClaim(
        claim_id="clm_001",
        original_text="Indian Railways suspended passenger train operations in Delhi.",
        text="Indian Railways suspended passenger train operations in Delhi.",
        normalized_claim="Indian Railways suspended passenger train operations in Delhi.",
        entities=["Indian Railways"],
        locations=["Delhi"],
        claim_type="policy",
        check_worthiness=True,
    )
    claim_2 = AtomicClaim(
        claim_id="clm_002",
        original_text="Drinking water pipeline in Ward 14 has been chemically contaminated.",
        text="Drinking water pipeline in Ward 14 has been chemically contaminated.",
        normalized_claim="Drinking water pipeline in Ward 14 has been chemically contaminated.",
        locations=["Ward 14"],
        claim_type="health",
        check_worthiness=True,
    )

    graph = claim_dependency_service.analyze_dependencies([claim_1, claim_2])

    # No dependency edges must be created for independent facts
    assert len(graph.dependencies) == 0
    assert set(graph.independent_claim_ids) == {"clm_001", "clm_002"}
    assert len(graph.execution_order) == 2


# ==============================================================================
# 3. Duplicate Claims
# ==============================================================================

def test_duplicate_claims_detection():
    """
    Identifies claims stating the exact same proposition as DUPLICATE_OF,
    allowing verification results to be reused and avoiding duplicate retrieval.
    """
    claim_1 = AtomicClaim(
        claim_id="clm_001",
        original_text="The government has launched Scheme X in 2026.",
        text="The government has launched Scheme X in 2026.",
        normalized_claim="The government has launched Scheme X in 2026.",
        entities=["Scheme X"],
        dates=["2026"],
        claim_type="policy",
        check_worthiness=True,
    )
    claim_2 = AtomicClaim(
        claim_id="clm_002",
        original_text="Scheme X has been launched by the government in 2026.",
        text="Scheme X has been launched by the government in 2026.",
        normalized_claim="Scheme X has been launched by the government in 2026.",
        entities=["Scheme X"],
        dates=["2026"],
        claim_type="policy",
        check_worthiness=True,
    )

    graph = claim_dependency_service.analyze_dependencies([claim_1, claim_2])

    assert len(graph.dependencies) == 1
    dep = graph.dependencies[0]
    assert dep.parent_claim_id == "clm_001"
    assert dep.child_claim_id == "clm_002"
    assert dep.relationship == DependencyRelationship.DUPLICATE_OF


def test_exact_duplicate_claims():
    """Identifies verbatim identical claims."""
    claim_1 = AtomicClaim(
        claim_id="clm_001",
        original_text="UPI has been banned in India.",
        text="UPI has been banned in India.",
        normalized_claim="UPI has been banned in India.",
        entities=["UPI"],
        locations=["India"],
    )
    claim_2 = AtomicClaim(
        claim_id="clm_002",
        original_text="UPI has been banned in India.",
        text="UPI has been banned in India.",
        normalized_claim="UPI has been banned in India.",
        entities=["UPI"],
        locations=["India"],
    )

    graph = claim_dependency_service.analyze_dependencies([claim_1, claim_2])
    assert len(graph.dependencies) == 1
    assert graph.dependencies[0].relationship == DependencyRelationship.DUPLICATE_OF


# ==============================================================================
# 4. Contradictory Claims
# ==============================================================================

def test_contradictory_claims_direct_negation():
    """
    Identifies mutually exclusive assertions on the same subject as CONTRADICTS.
    (e.g. 'Schools are closed' vs 'Schools will remain open').
    """
    claim_1 = AtomicClaim(
        claim_id="clm_001",
        original_text="All schools are closed tomorrow.",
        text="All schools are closed tomorrow.",
        normalized_claim="All schools are closed tomorrow.",
        dates=["tomorrow"],
        claim_type="policy",
        check_worthiness=True,
    )
    claim_2 = AtomicClaim(
        claim_id="clm_002",
        original_text="All schools will remain open tomorrow.",
        text="All schools will remain open tomorrow.",
        normalized_claim="All schools will remain open tomorrow.",
        dates=["tomorrow"],
        claim_type="policy",
        check_worthiness=True,
    )

    graph = claim_dependency_service.analyze_dependencies([claim_1, claim_2])

    assert len(graph.dependencies) == 1
    dep = graph.dependencies[0]
    assert dep.parent_claim_id == "clm_001"
    assert dep.child_claim_id == "clm_002"
    assert dep.relationship == DependencyRelationship.CONTRADICTS


def test_contradictory_claims_numeric_discrepancy():
    """
    Identifies incompatible numerical figures asserted for the same scheme.
    (e.g. ₹10,000 vs ₹50,000 payout).
    """
    claim_1 = AtomicClaim(
        claim_id="clm_001",
        original_text="Scheme X gives ₹10,000 to every citizen.",
        text="Scheme X gives ₹10,000 to every citizen.",
        normalized_claim="Scheme X gives ₹10,000 to every citizen.",
        entities=["scheme x"],
        numbers=[10000],
        claim_type="financial",
        check_worthiness=True,
    )
    claim_2 = AtomicClaim(
        claim_id="clm_002",
        original_text="Scheme X gives ₹50,000 to every citizen.",
        text="Scheme X gives ₹50,000 to every citizen.",
        normalized_claim="Scheme X gives ₹50,000 to every citizen.",
        entities=["scheme x"],
        numbers=[50000],
        claim_type="financial",
        check_worthiness=True,
    )

    graph = claim_dependency_service.analyze_dependencies([claim_1, claim_2])

    assert len(graph.dependencies) == 1
    assert graph.dependencies[0].relationship == DependencyRelationship.CONTRADICTS


# ==============================================================================
# 5. Multi-Hop Dependencies & Mixed Collections
# ==============================================================================

def test_multi_hop_dependencies_execution_order():
    """
    Tests sequential chain of dependencies:
    Claim 1 (Launch PMSSY) -> Claim 2 (PMSSY grant details) -> Claim 3 (Registration portal)
    Execution order must place root antecedent first.
    """
    claim_1 = AtomicClaim(
        claim_id="clm_001",
        original_text="Ministry of Education launched the PMSSY scholarship scheme.",
        text="Ministry of Education launched the PMSSY scholarship scheme.",
        normalized_claim="Ministry of Education launched the PMSSY scholarship scheme.",
        entities=["PMSSY", "Ministry of Education"],
        claim_type="policy",
        check_worthiness=True,
    )
    claim_2 = AtomicClaim(
        claim_id="clm_002",
        original_text="PMSSY gives ₹50,000 DBT grant to college students.",
        text="PMSSY gives ₹50,000 DBT grant to college students.",
        normalized_claim="PMSSY gives ₹50,000 DBT grant to college students.",
        entities=["PMSSY"],
        numbers=[50000],
        claim_type="financial",
        check_worthiness=True,
    )
    claim_3 = AtomicClaim(
        claim_id="clm_003",
        original_text="Under this scheme, applicants must register on pmssy-gov.in.",
        text="Under this scheme, applicants must register on pmssy-gov.in.",
        normalized_claim="Under this scheme, applicants must register on pmssy-gov.in.",
        entities=["pmssy-gov.in"],
        claim_type="policy",
        check_worthiness=True,
    )

    graph = claim_dependency_service.analyze_dependencies([claim_1, claim_2, claim_3])

    # Claim 1 is the root antecedent
    assert graph.execution_order.index("clm_001") < graph.execution_order.index("clm_002")


def test_mixed_collection_with_independent_claim():
    """
    Tests a set of 3 claims where two are dependent and one is completely independent.
    Ensures independent claim has no bogus edges.
    """
    c_parent = AtomicClaim(
        claim_id="clm_001",
        original_text="Government launched scheme X.",
        text="Government launched scheme X.",
        normalized_claim="Government launched scheme X.",
        entities=["scheme x"],
    )
    c_child = AtomicClaim(
        claim_id="clm_002",
        original_text="Scheme X gives ₹10,000 to every citizen.",
        text="Scheme X gives ₹10,000 to every citizen.",
        normalized_claim="Scheme X gives ₹10,000 to every citizen.",
        entities=["scheme x"],
        numbers=[10000],
    )
    c_independent = AtomicClaim(
        claim_id="clm_003",
        original_text="Indian Railways suspended passenger trains in Delhi.",
        text="Indian Railways suspended passenger trains in Delhi.",
        normalized_claim="Indian Railways suspended passenger trains in Delhi.",
        entities=["Indian Railways"],
        locations=["Delhi"],
    )

    graph = claim_dependency_service.analyze_dependencies([c_parent, c_child, c_independent])

    # Exactly 1 dependency edge
    assert len(graph.dependencies) == 1
    assert graph.dependencies[0].parent_claim_id == "clm_001"
    assert graph.dependencies[0].child_claim_id == "clm_002"

    # Claim 3 is recorded as independent
    assert "clm_003" in graph.independent_claim_ids


# ==============================================================================
# 6. End-to-End Extraction & Dependency Pipeline
# ==============================================================================

def test_pipeline_from_extracted_claims_to_dependency_graph():
    """
    Verifies that claims extracted from a citizen forward can be piped
    directly into dependency analysis.
    """
    message = "Government launched scheme X and Scheme X gives ₹10,000 to every citizen."
    extraction = claim_extractor_service.extract_claims(message)

    assert len(extraction.claims) == 2

    graph = claim_dependency_service.analyze_dependencies(extraction.claims)

    assert len(graph.dependencies) == 1
    assert graph.dependencies[0].parent_claim_id == "clm_001"
    assert graph.dependencies[0].child_claim_id == "clm_002"
    assert graph.dependencies[0].relationship == DependencyRelationship.DEPENDS_ON


# ==============================================================================
# 7. FastAPI Endpoint Integration
# ==============================================================================

@pytest.mark.asyncio
async def test_api_analyze_dependencies_endpoint():
    """Tests POST /api/v1/claims/analyze-dependencies endpoint."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        payload = {
            "claims": [
                {
                    "claim_id": "clm_001",
                    "original_text": "Government launched scheme X.",
                    "text": "Government launched scheme X.",
                    "normalized_claim": "Government launched scheme X.",
                    "entities": ["scheme x"],
                    "numbers": [],
                    "dates": [],
                    "locations": [],
                    "claim_type": "policy",
                    "check_worthiness": True,
                },
                {
                    "claim_id": "clm_002",
                    "original_text": "Scheme X gives ₹10,000 to every citizen.",
                    "text": "Scheme X gives ₹10,000 to every citizen.",
                    "normalized_claim": "Scheme X gives ₹10,000 to every citizen.",
                    "entities": ["scheme x"],
                    "numbers": [10000],
                    "dates": [],
                    "locations": [],
                    "claim_type": "financial",
                    "check_worthiness": True,
                },
            ]
        }
        response = await client.post("/api/v1/claims/analyze-dependencies", json=payload)
        assert response.status_code == 200
        data = response.json()

        assert "dependencies" in data
        assert len(data["dependencies"]) == 1
        assert data["dependencies"][0]["parent_claim_id"] == "clm_001"
        assert data["dependencies"][0]["child_claim_id"] == "clm_002"
        assert data["dependencies"][0]["relationship"] == "DEPENDS_ON"
        assert data["execution_order"] == ["clm_001", "clm_002"]
