from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator


class UserFeedbackType(str, Enum):
    """Permissible citizen feedback ratings on verification results."""
    CORRECT = "CORRECT"
    WRONG = "WRONG"
    UNCLEAR = "UNCLEAR"


class ReviewStatus(str, Enum):
    """Review queue workflow states."""
    PENDING = "PENDING"
    UNDER_REVIEW = "UNDER_REVIEW"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"


class ReviewItem(BaseModel):
    """
    Citizen feedback review queue entity.

    CRITICAL ARCHITECTURAL INVARIANT:
    User feedback must NEVER directly modify Shared Claim Memory.
    Instead:
    feedback -> review_queue -> human/admin review -> decision -> optional memory update
    """
    review_id: str = Field(..., min_length=2, description="Unique review identifier")
    check_id: str = Field(..., min_length=1, description="Associated check ID")
    claim_id: Optional[str] = Field(default=None, description="Associated atomic claim ID if applicable")
    feedback: str = Field(..., description="User feedback verdict: CORRECT, WRONG, UNCLEAR")
    status: str = Field(default="PENDING", description="Status in review queue: PENDING, RESOLVED, REJECTED")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = Field(default=None, description="Timestamp when human review was conducted")
    reviewer: Optional[str] = Field(default=None, description="Human auditor or admin reviewer identifier")
    resolution: Optional[str] = Field(default=None, description="Auditor rationale or decision outcome")

    @field_validator("feedback")
    @classmethod
    def validate_feedback(cls, v: str) -> str:
        clean = (v or "").strip().upper()
        if clean not in ("CORRECT", "WRONG", "UNCLEAR"):
            raise ValueError(f"Invalid feedback '{v}'. Permissible values: CORRECT, WRONG, UNCLEAR")
        return clean


class FeedbackSubmissionRequest(BaseModel):
    """Request payload for POST /api/v1/feedback."""
    check_id: str = Field(..., min_length=1, description="Associated check ID")
    claim_id: Optional[str] = Field(default=None, description="Associated atomic claim ID")
    feedback: str = Field(..., description="User feedback: CORRECT, WRONG, UNCLEAR")

    @field_validator("feedback")
    @classmethod
    def validate_feedback_choice(cls, v: str) -> str:
        clean = (v or "").strip().upper()
        if clean not in ("CORRECT", "WRONG", "UNCLEAR"):
            raise ValueError(f"Invalid feedback '{v}'. Permissible values: CORRECT, WRONG, UNCLEAR")
        return clean


class ReviewDecisionRequest(BaseModel):
    """Request payload for applying an auditor decision to an item in review_queue."""
    reviewer: str = Field(..., min_length=1, description="Admin/auditor identifier")
    decision: str = Field(..., description="Review outcome: e.g. RESOLVED, REJECTED, OVERTURNED, CONFIRMED")
    resolution: Optional[str] = Field(default=None, description="Auditor explanation or notes")
    update_claim_memory: bool = Field(default=False, description="Whether to update Shared Claim Memory upon decision")
    new_verdict: Optional[str] = Field(default=None, description="Optional revised verdict if memory update requested")
