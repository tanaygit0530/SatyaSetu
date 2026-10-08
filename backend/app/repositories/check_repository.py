from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError, ResourceNotFoundException
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import Check, ProcessingStage, VerificationResult
from app.schemas.enums import ProcessingStatus


class CheckRepository(BaseFirestoreRepository):
    """Repository handling CRUD operations for citizen verification checks."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.CHECKS, db=db)
        # Local in-memory fallback store for offline / unconfigured operation
        self._local_checks: Dict[str, Check] = {}

    def create_check(self, check: Union[Check, Dict[str, Any]]) -> Check:
        """
        Persists a newly ingested citizen verification check document.
        """
        check_obj = check if isinstance(check, Check) else Check.model_validate(check)
        self._local_checks[check_obj.check_id] = check_obj
        data = self.serialize_model(check_obj)
        try:
            doc_ref = self.collection.document(check_obj.check_id)
            doc_ref.set(data)
            return check_obj
        except Exception as e:
            if self._db is not None:
                raise DatabaseOperationError(
                    f"Failed to create check '{check_obj.check_id}': {str(e)}"
                ) from e
            return check_obj

    def get_check(self, check_id: str) -> Optional[Check]:
        """
        Retrieves a check document by its unique check ID.
        Returns None if not found.
        """
        local_rec = self._local_checks.get(check_id)
        try:
            doc_ref = self.collection.document(check_id)
            doc = doc_ref.get()
            if not doc.exists:
                return local_rec
            return Check.model_validate(doc.to_dict())
        except Exception as e:
            if self._db is not None:
                raise DatabaseOperationError(
                    f"Failed to retrieve check '{check_id}': {str(e)}"
                ) from e
            return local_rec

    def update_check_status(
        self,
        check_id: str,
        status: Union[ProcessingStatus, str],
        stage: Optional[Union[ProcessingStage, Dict[str, Any]]] = None,
    ) -> Optional[Check]:
        """
        Updates the processing status and stage progression for an active check.
        """
        status_val = status.value if isinstance(status, ProcessingStatus) else str(status)
        existing = self.get_check(check_id)
        if not existing:
            return None

        existing.status = ProcessingStatus(status_val)
        existing.updated_at = datetime.now(timezone.utc)
        if stage is not None:
            stage_obj = stage if isinstance(stage, ProcessingStage) else ProcessingStage.model_validate(stage)
            existing.stages.append(stage_obj)

        self._local_checks[check_id] = existing

        update_payload: Dict[str, Any] = {
            "status": status_val,
            "updated_at": existing.updated_at.isoformat(),
            "stages": [s.model_dump(mode="json") for s in existing.stages],
        }

        try:
            doc_ref = self.collection.document(check_id)
            doc_ref.update(update_payload)
            return existing
        except Exception as e:
            if self._db is not None:
                raise DatabaseOperationError(
                    f"Failed to update status for check '{check_id}': {str(e)}"
                ) from e
            return existing

    def save_verification_result(
        self,
        check_id: str,
        result: Union[VerificationResult, Dict[str, Any]],
    ) -> Optional[Check]:
        """
        Attaches the final computed VerificationResult to the check and marks status COMPLETED.
        """
        res_obj = result if isinstance(result, VerificationResult) else VerificationResult.model_validate(result)
        existing = self.get_check(check_id)
        if not existing:
            return None

        existing.result = res_obj
        existing.status = ProcessingStatus.COMPLETED
        existing.updated_at = datetime.now(timezone.utc)
        self._local_checks[check_id] = existing

        update_payload: Dict[str, Any] = {
            "result": self.serialize_model(res_obj),
            "status": ProcessingStatus.COMPLETED.value,
            "updated_at": existing.updated_at.isoformat(),
        }

        try:
            doc_ref = self.collection.document(check_id)
            doc_ref.update(update_payload)
            return existing
        except Exception as e:
            if self._db is not None:
                raise DatabaseOperationError(
                    f"Failed to save verification result for check '{check_id}': {str(e)}"
                ) from e
            return existing

    def list_checks(
        self,
        limit: int = 50,
        status: Optional[Union[ProcessingStatus, str]] = None,
        user_id: Optional[str] = None,
    ) -> List[Check]:
        """
        Queries recent verification checks, optionally filtered by status or user ID.
        """
        try:
            query = self.collection
            if status is not None:
                st_val = status.value if isinstance(status, ProcessingStatus) else str(status)
                query = query.where("status", "==", st_val)
            if user_id is not None:
                query = query.where("user_id", "==", user_id)

            query = query.limit(limit)
            docs = query.stream()
            results: List[Check] = []
            for doc in docs:
                results.append(Check.model_validate(doc.to_dict()))
            return results
        except Exception as e:
            if self._db is not None:
                raise DatabaseOperationError(f"Failed to list checks: {str(e)}") from e
            filtered = list(self._local_checks.values())
            if status is not None:
                st_val = status.value if isinstance(status, ProcessingStatus) else str(status)
                filtered = [c for c in filtered if c.status.value == st_val]
            if user_id is not None:
                filtered = [c for c in filtered if c.user_id == user_id]
            return filtered[:limit]

    def delete_check(self, check_id: str) -> bool:
        """
        Deletes a check document by ID. Returns True if deleted.
        """
        self._local_checks.pop(check_id, None)
        try:
            doc_ref = self.collection.document(check_id)
            doc_ref.delete()
            return True
        except Exception as e:
            if self._db is not None:
                raise DatabaseOperationError(
                    f"Failed to delete check '{check_id}': {str(e)}"
                ) from e
            return True
