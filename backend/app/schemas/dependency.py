from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.claim import AtomicClaim


class DependencyRelationship(str, Enum):
    """
    Nature of dependency relationship between two atomic claims.
    Only created when they materially affect verification.
    """
    DEPENDS_ON = "DEPENDS_ON"      # Child claim presupposes the factual veracity of parent claim
    DUPLICATE_OF = "DUPLICATE_OF"  # Both claims assert the exact same proposition
    CONTRADICTS = "CONTRADICTS"    # Claims make mutually exclusive or directly contradictory statements


class ClaimDependency(BaseModel):
    """
    Directed relationship between two claims.
    Example:
    Claim A: "Government launched scheme X."
    Claim B: "Scheme X gives ₹10,000 to every citizen."
    {
      "parent_claim_id": "clm_001",
      "child_claim_id": "clm_002",
      "relationship": "DEPENDS_ON"
    }
    """
    parent_claim_id: str = Field(
        ...,
        description="ID of antecedent or reference claim (e.g. 'clm_001')",
    )
    child_claim_id: str = Field(
        ...,
        description="ID of dependent, duplicate, or contradictory claim (e.g. 'clm_002')",
    )
    relationship: DependencyRelationship = Field(
        default=DependencyRelationship.DEPENDS_ON,
        description="Nature of the dependency link (DEPENDS_ON, DUPLICATE_OF, CONTRADICTS)",
    )
    reason: Optional[str] = Field(
        None,
        description="Material explanation for how this dependency affects verification",
    )


class ClaimDependencyGraph(BaseModel):
    """
    Dependency graph representation containing only material dependencies,
    avoiding unnecessary graph complexity.
    """
    dependencies: List[ClaimDependency] = Field(
        default_factory=list,
        description="Active material relationships (DEPENDS_ON, DUPLICATE_OF, CONTRADICTS)",
    )
    execution_order: List[str] = Field(
        default_factory=list,
        description="Topologically sorted claim IDs ensuring antecedent claims are verified first",
    )
    independent_claim_ids: List[str] = Field(
        default_factory=list,
        description="Claims that operate completely independently with no dependencies",
    )


class DependencyAnalysisInput(BaseModel):
    """Input payload for dependency analysis."""
    claims: List[AtomicClaim] = Field(
        ...,
        min_length=1,
        description="List of atomic claims to analyze for dependencies",
    )
