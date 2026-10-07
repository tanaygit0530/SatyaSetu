from typing import Any, Dict, List, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import Feedback


class FeedbackRepository(BaseFirestoreRepository):
    """Repository handling persistence for citizen disputes and auditor feedback."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.FEEDBACK, db=db)

    def create_feedback(self, feedback: Union[Feedback, Dict[str, Any]]) -> Feedback:
        """
        Stores citizen feedback or dispute with counter-evidence.
        """
        fb_obj = feedback if isinstance(feedback, Feedback) else Feedback.model_validate(feedback)
        data = self.serialize_model(fb_obj)
        try:
            doc_ref = self.collection.document(fb_obj.feedback_id)
            doc_ref.set(data)
            return fb_obj
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to record feedback '{fb_obj.feedback_id}': {str(e)}"
            ) from e

    def get_feedback(self, feedback_id: str) -> Optional[Feedback]:
        """
        Retrieves feedback document by ID.
        """
        try:
            doc_ref = self.collection.document(feedback_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            return Feedback.model_validate(doc.to_dict())
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to retrieve feedback '{feedback_id}': {str(e)}"
            ) from e

    def get_feedback_by_check_id(self, check_id: str) -> List[Feedback]:
        """
        Retrieves all feedback submitted against a specific verification check.
        """
        try:
            docs = self.collection.where("check_id", "==", check_id).stream()
            results: List[Feedback] = []
            for doc in docs:
                results.append(Feedback.model_validate(doc.to_dict()))
            return results
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to retrieve feedback for check '{check_id}': {str(e)}"
            ) from e

    def list_feedback(self, limit: int = 50) -> List[Feedback]:
        """
        Lists recent feedback submissions.
        """
        try:
            docs = self.collection.limit(limit).stream()
            results: List[Feedback] = []
            for doc in docs:
                results.append(Feedback.model_validate(doc.to_dict()))
            return results
        except Exception as e:
            raise DatabaseOperationError(f"Failed to list feedback: {str(e)}") from e
