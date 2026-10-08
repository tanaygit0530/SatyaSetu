from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError, FirebaseConfigurationError
from app.core.logging import logger
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import ReviewItem, ReviewQueueItem


class ReviewRepository(BaseFirestoreRepository):
    """Repository managing auditor queues for dispute escalations, citizen feedback, and ambiguous claims."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.REVIEW_QUEUE, db=db)
        self._local_review_items: Dict[str, ReviewItem] = {}
        self._local_queue_items: Dict[str, ReviewQueueItem] = {}

    def create_review_item(
        self,
        item: Union[ReviewItem, ReviewQueueItem, Dict[str, Any]],
    ) -> Union[ReviewItem, ReviewQueueItem]:
        """
        Enqueues an item for human auditor inspection.
        Supports both ReviewItem (feedback) and ReviewQueueItem.
        """
        if hasattr(item, "feedback") or (isinstance(item, dict) and "feedback" in item):
            item_obj = item if isinstance(item, ReviewItem) else ReviewItem.model_validate(item)
            self._local_review_items[item_obj.review_id] = item_obj
            data = self.serialize_model(item_obj)
            try:
                doc_ref = self.collection.document(item_obj.review_id)
                doc_ref.set(data)
                return item_obj
            except FirebaseConfigurationError:
                return item_obj
            except Exception as e:
                logger.warning("Could not persist ReviewItem to Firestore: %s", e)
                return item_obj
        else:
            queue_obj = item if isinstance(item, ReviewQueueItem) else ReviewQueueItem.model_validate(item)
            self._local_queue_items[queue_obj.review_id] = queue_obj
            data = self.serialize_model(queue_obj)
            try:
                doc_ref = self.collection.document(queue_obj.review_id)
                doc_ref.set(data)
                return queue_obj
            except FirebaseConfigurationError:
                return queue_obj
            except Exception as e:
                raise DatabaseOperationError(
                    f"Failed to create review item '{queue_obj.review_id}': {str(e)}"
                ) from e

    def get_review_item(self, review_id: str) -> Optional[Union[ReviewItem, ReviewQueueItem]]:
        """
        Retrieves a review item by review_id.
        """
        if review_id in self._local_review_items:
            return self._local_review_items[review_id]
        if review_id in self._local_queue_items:
            return self._local_queue_items[review_id]

        try:
            doc_ref = self.collection.document(review_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            doc_data = doc.to_dict() or {}
            if "feedback" in doc_data:
                obj = ReviewItem.model_validate(doc_data)
                self._local_review_items[review_id] = obj
                return obj
            else:
                q_obj = ReviewQueueItem.model_validate(doc_data)
                self._local_queue_items[review_id] = q_obj
                return q_obj
        except FirebaseConfigurationError:
            return None
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
    ) -> Optional[Union[ReviewItem, ReviewQueueItem]]:
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
            if hasattr(item, "auditor_notes"):
                item.auditor_notes = auditor_notes
            if hasattr(item, "resolution"):
                item.resolution = auditor_notes
        if assigned_to is not None:
            update_payload["assigned_to"] = assigned_to
            if hasattr(item, "assigned_to"):
                item.assigned_to = assigned_to
            if hasattr(item, "reviewer"):
                item.reviewer = assigned_to

        item.status = status
        if hasattr(item, "reviewed_at"):
            item.reviewed_at = datetime.now(timezone.utc)

        try:
            doc_ref = self.collection.document(review_id)
            doc_ref.update(update_payload)
        except Exception as e:
            logger.debug("Local update fallback for review item %s: %s", review_id, e)

        return item

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
                doc_d = doc.to_dict() or {}
                if "priority" in doc_d or "reason" in doc_d:
                    results.append(ReviewQueueItem.model_validate(doc_d))
            if not results and self._local_queue_items:
                results = [
                    q for q in self._local_queue_items.values()
                    if q.status == "PENDING" and (priority is None or q.priority == priority)
                ]
            return results[:limit]
        except Exception as e:
            if self._local_queue_items:
                return [
                    q for q in self._local_queue_items.values()
                    if q.status == "PENDING" and (priority is None or q.priority == priority)
                ][:limit]
            raise DatabaseOperationError(
                f"Failed to list pending reviews: {str(e)}"
            ) from e

    def list_feedback_items(
        self,
        status: Optional[str] = None,
        limit: int = 50,
    ) -> List[ReviewItem]:
        """
        Lists ReviewItems enqueued from citizen feedback submissions.
        """
        try:
            query = self.collection
            if status is not None:
                query = query.where("status", "==", status)
            docs = query.limit(limit).stream()
            results: List[ReviewItem] = []
            for doc in docs:
                data = doc.to_dict() or {}
                if "feedback" in data:
                    results.append(ReviewItem.model_validate(data))
            if not results and self._local_review_items:
                results = [
                    item for item in self._local_review_items.values()
                    if status is None or item.status == status
                ]
            return results[:limit]
        except Exception:
            return [
                item for item in self._local_review_items.values()
                if status is None or item.status == status
            ][:limit]

    def delete_review_item(self, review_id: str) -> bool:
        """
        Removes a review item from the queue.
        """
        self._local_review_items.pop(review_id, None)
        self._local_queue_items.pop(review_id, None)
        try:
            doc_ref = self.collection.document(review_id)
            doc_ref.delete()
            return True
        except Exception as e:
            logger.debug("Firestore delete notice: %s", e)
            return True
