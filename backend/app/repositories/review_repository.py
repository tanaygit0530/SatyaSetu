from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import ReviewQueueItem


class ReviewRepository(BaseFirestoreRepository):
    """Repository managing auditor queues for dispute escalations and ambiguous claims."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.REVIEW_QUEUE, db=db)

    def create_review_item(
        self,
        item: Union[ReviewQueueItem, Dict[str, Any]],
    ) -> ReviewQueueItem:
        """
        Enqueues an item for human auditor inspection.
        """
        item_obj = item if isinstance(item, ReviewQueueItem) else ReviewQueueItem.model_validate(item)
        data = self.serialize_model(item_obj)
        try:
            doc_ref = self.collection.document(item_obj.review_id)
            doc_ref.set(data)
            return item_obj
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to create review item '{item_obj.review_id}': {str(e)}"
            ) from e

    def get_review_item(self, review_id: str) -> Optional[ReviewQueueItem]:
        """
        Retrieves a review item by review_id.
        """
        try:
            doc_ref = self.collection.document(review_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            return ReviewQueueItem.model_validate(doc.to_dict())
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to retrieve review item '{review_id}': {str(e)}"
            ) from e

    def update_review_status(
        self,
        review_id: str,
        status: str,
        auditor_notes: Optional[str] = None,
        assigned_to: Optional[str] = None,
    ) -> Optional[ReviewQueueItem]:
        """
        Updates review status, auditor notes, or assignment.
        """
        item = self.get_review_item(review_id)
        if not item:
            return None

        update_payload: Dict[str, Any] = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        if auditor_notes is not None:
            update_payload["auditor_notes"] = auditor_notes
        if assigned_to is not None:
            update_payload["assigned_to"] = assigned_to

        try:
            doc_ref = self.collection.document(review_id)
            doc_ref.update(update_payload)
            item.status = status
            if auditor_notes is not None:
                item.auditor_notes = auditor_notes
            if assigned_to is not None:
                item.assigned_to = assigned_to
            return item
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to update review item '{review_id}': {str(e)}"
            ) from e

    def list_pending_reviews(
        self,
        priority: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReviewQueueItem]:
        """
        Retrieves pending review items sorted or filtered by priority.
        """
        try:
            query = self.collection.where("status", "==", "PENDING")
            if priority is not None:
                query = query.where("priority", "==", priority)
            docs = query.limit(limit).stream()
            results: List[ReviewQueueItem] = []
            for doc in docs:
                results.append(ReviewQueueItem.model_validate(doc.to_dict()))
            return results
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to list pending reviews: {str(e)}"
            ) from e

    def delete_review_item(self, review_id: str) -> bool:
        """
        Removes a review item from the queue.
        """
        try:
            doc_ref = self.collection.document(review_id)
            doc_ref.delete()
            return True
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to delete review item '{review_id}': {str(e)}"
            ) from e
