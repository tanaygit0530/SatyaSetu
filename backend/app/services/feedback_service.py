import uuid
from datetime import datetime, timezone
from typing import List, Optional, Union

from app.core.exceptions import InvalidInputException, ResourceNotFoundException
from app.core.logging import logger
from app.repositories.review_repository import ReviewRepository
from app.schemas.enums import Verdict
from app.schemas.review import ReviewItem, UserFeedbackType
from app.services.claim_memory import SharedClaimMemoryService, claim_memory_service


class FeedbackService:
    """
    Service handling citizen feedback and the human auditor review queue.

    CRITICAL INVARIANT:
    User feedback must NEVER directly modify Shared Claim Memory.
    Pipeline:
    feedback -> review_queue -> human/admin review -> decision -> optional memory update
    """

    def __init__(
        self,
        review_repository: Optional[ReviewRepository] = None,
        claim_memory: Optional[SharedClaimMemoryService] = None,
    ):
        self.review_repo = review_repository or ReviewRepository()
        self.claim_memory = claim_memory or claim_memory_service

    def submit_feedback(
        self,
        check_id: str,
        feedback: str,
        claim_id: Optional[str] = None,
    ) -> ReviewItem:
        """
        Submits citizen feedback for a verification check or claim.
        Enqueues a ReviewItem into review_queue for human auditor triage.

        CRITICAL: Never modifies Shared Claim Memory here!
        """
        if not check_id or not check_id.strip():
            raise InvalidInputException("check_id is required for feedback submission.")

        norm_feedback = (feedback or "").strip().upper()
        if norm_feedback not in (UserFeedbackType.CORRECT.value, UserFeedbackType.WRONG.value, UserFeedbackType.UNCLEAR.value):
            raise InvalidInputException(
                f"Invalid feedback '{feedback}'. Allowed feedback values: CORRECT, WRONG, UNCLEAR."
            )

        review_id = f"rev_{uuid.uuid4().hex[:10]}"
        review_item = ReviewItem(
            review_id=review_id,
            check_id=check_id.strip(),
            claim_id=claim_id.strip() if claim_id else None,
            feedback=norm_feedback,
            status="PENDING",
            created_at=datetime.now(timezone.utc),
            reviewed_at=None,
            reviewer=None,
            resolution=None,
        )

        # Enqueue in review_queue repository
        # Under NO circumstances is Shared Claim Memory modified here
        self.review_repo.create_review_item(review_item)

        logger.info(
            "Enqueued user feedback into review_queue: review_id=%s, check_id=%s, claim_id=%s, feedback=%s",
            review_id,
            check_id,
            claim_id,
            norm_feedback,
        )

        return review_item

    def list_review_queue(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReviewItem]:
        """Lists items in review queue for human/admin inspection."""
        return self.review_repo.list_feedback_items(status=status, limit=limit)

    def get_review_item(self, review_id: str) -> ReviewItem:
        """Retrieves a single review item by ID."""
        item = self.review_repo.get_review_item(review_id)
        if not item or not isinstance(item, ReviewItem):
            raise ResourceNotFoundException(f"Review item '{review_id}' not found.")
        return item

    def apply_review_decision(
        self,
        review_id: str,
        reviewer: str,
        decision: str,
        resolution: Optional[str] = None,
        update_memory: bool = False,
        new_verdict: Optional[Union[Verdict, str]] = None,
        claim_text: Optional[str] = None,
    ) -> ReviewItem:
        """
        Executes human/admin review step.

        Workflow:
        feedback -> review_queue -> human/admin review -> decision -> optional memory update
        """
        item = self.get_review_item(review_id)
        if not reviewer or not reviewer.strip():
            raise InvalidInputException("Reviewer identification is required for auditing.")

        clean_decision = (decision or "RESOLVED").strip().upper()
        now = datetime.now(timezone.utc)

        item.status = clean_decision
        item.reviewer = reviewer.strip()
        item.reviewed_at = now
        item.resolution = resolution or f"Decision '{clean_decision}' applied by reviewer '{reviewer}'"

        # Update review item in repository
        self.review_repo.create_review_item(item)

        # Optional memory update: only when explicitly sanctioned by human auditor
        if update_memory and self.claim_memory is not None:
            logger.info("Human review authorized memory update for review %s", review_id)
            if claim_text:
                target_verdict = Verdict.FALSE
                if new_verdict:
                    try:
                        target_verdict = Verdict(new_verdict) if isinstance(new_verdict, str) else new_verdict
                    except ValueError:
                        target_verdict = Verdict.FALSE

                try:
                    self.claim_memory.store_claim(
                        claim_text=claim_text,
                        verdict=target_verdict,
                        confidence="HIGH",
                        explanation=item.resolution or "Updated following auditor review.",
                    )
                    logger.info("Shared Claim Memory updated following human review decision.")
                except Exception as e:
                    logger.warning("Optional claim memory update encountered error: %s", e)

        return item


# Global singleton instance
feedback_service = FeedbackService()
