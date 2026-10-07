from typing import Any, Dict, List, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import Evidence


class EvidenceRepository(BaseFirestoreRepository):
    """Repository handling persistence for statutory and official evidence citations."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.EVIDENCE, db=db)

    def save_evidence(self, evidence: Union[Evidence, Dict[str, Any]]) -> Evidence:
        """
        Persists an official evidence citation record.
        """
        ev_obj = evidence if isinstance(evidence, Evidence) else Evidence.model_validate(evidence)
        data = self.serialize_model(ev_obj)
        try:
            doc_ref = self.collection.document(ev_obj.evidence_id)
            doc_ref.set(data)
            return ev_obj
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to save evidence '{ev_obj.evidence_id}': {str(e)}"
            ) from e

    def get_evidence(self, evidence_id: str) -> Optional[Evidence]:
        """
        Retrieves evidence by unique evidence_id. Returns None if absent.
        """
        try:
            doc_ref = self.collection.document(evidence_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            return Evidence.model_validate(doc.to_dict())
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to retrieve evidence '{evidence_id}': {str(e)}"
            ) from e

    def get_evidence_by_url(self, source_url: str) -> Optional[Evidence]:
        """
        Finds existing evidence record matching an exact source URL.
        """
        try:
            docs = self.collection.where("source_url", "==", source_url).limit(1).stream()
            for doc in docs:
                return Evidence.model_validate(doc.to_dict())
            return None
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to query evidence by url '{source_url}': {str(e)}"
            ) from e

    def get_evidence_multi(self, evidence_ids: List[str]) -> List[Evidence]:
        """
        Retrieves multiple evidence records by a list of evidence IDs.
        """
        results: List[Evidence] = []
        for ev_id in evidence_ids:
            ev = self.get_evidence(ev_id)
            if ev is not None:
                results.append(ev)
        return results

    def list_evidence(
        self,
        tier: Optional[int] = None,
        limit: int = 50,
    ) -> List[Evidence]:
        """
        Lists stored evidence records, optionally filtered by tier (1, 2, or 3).
        """
        try:
            query = self.collection
            if tier is not None:
                query = query.where("source_tier", "==", tier)
            docs = query.limit(limit).stream()
            results: List[Evidence] = []
            for doc in docs:
                results.append(Evidence.model_validate(doc.to_dict()))
            return results
        except Exception as e:
            raise DatabaseOperationError(f"Failed to list evidence: {str(e)}") from e

    def delete_evidence(self, evidence_id: str) -> bool:
        """
        Deletes an evidence record by ID.
        """
        try:
            doc_ref = self.collection.document(evidence_id)
            doc_ref.delete()
            return True
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to delete evidence '{evidence_id}': {str(e)}"
            ) from e
