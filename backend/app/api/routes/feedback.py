from typing import List, Optional
from fastapi import APIRouter, status

from app.schemas.review import (
    FeedbackSubmissionRequest,
    ReviewDecisionRequest,
    ReviewItem,
)
from app.services.feedback_service import feedback_service

router = APIRouter(prefix="/feedback", tags=["Feedback & Review Queue"])


@router.post(
    "",
    response_model=ReviewItem,
    status_code=status.HTTP_201_CREATED,
    summary="Submit citizen feedback on a check or claim",
    description=(
        "Enqueues a ReviewItem into review_queue. "
        "User feedback NEVER directly modifies Shared Claim Memory; "
        "it is routed to human/admin review first."
    ),
)
async def submit_feedback_endpoint(payload: FeedbackSubmissionRequest) -> ReviewItem:
    """
    Submits user feedback: CORRECT, WRONG, UNCLEAR.
    Enqueues into review_queue for human inspection without touching Shared Claim Memory.
    """
    return feedback_service.submit_feedback(
        check_id=payload.check_id,
        feedback=payload.feedback,
        claim_id=payload.claim_id,
    )


@router.get(
    "/reviews",
    response_model=List[ReviewItem],
    status_code=status.HTTP_200_OK,
    summary="List review queue items for human/admin audit",
)
async def list_review_queue_endpoint(
    status_filter: Optional[str] = None,
    limit: int = 50,
) -> List[ReviewItem]:
    """Lists pending or processed feedback review items."""
    return feedback_service.list_review_queue(status=status_filter, limit=limit)


@router.get(
    "/reviews/{review_id}",
    response_model=ReviewItem,
    status_code=status.HTTP_200_OK,
    summary="Get details of a specific review item",
)
async def get_review_item_endpoint(review_id: str) -> ReviewItem:
    """Retrieves an individual review item by ID."""
    return feedback_service.get_review_item(review_id)


@router.post(
    "/reviews/{review_id}/decision",
    response_model=ReviewItem,
    status_code=status.HTTP_200_OK,
    summary="Apply human/admin review decision with optional memory update",
    description="Auditor records human resolution and optionally updates Shared Claim Memory if verified.",
)
async def apply_review_decision_endpoint(
    review_id: str,
    payload: ReviewDecisionRequest,
) -> ReviewItem:
    """Applies auditor decision and executes optional memory update."""
    return feedback_service.apply_review_decision(
        review_id=review_id,
        reviewer=payload.reviewer,
        decision=payload.decision,
        resolution=payload.resolution,
        update_memory=payload.update_claim_memory,
        new_verdict=payload.new_verdict,
    )
