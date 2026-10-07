from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import CacheRecord


class ClaimMemoryRepository(BaseFirestoreRepository):
    """Repository handling rumour memory and deduplication cache."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.CLAIM_MEMORY, db=db)

    def save_record(self, record: Union[CacheRecord, Dict[str, Any]]) -> CacheRecord:
        """
        Saves a verified rumour hash into persistent memory.
        """
        rec_obj = record if isinstance(record, CacheRecord) else CacheRecord.model_validate(record)
        data = self.serialize_model(rec_obj)
        try:
            doc_ref = self.collection.document(rec_obj.cache_id)
            doc_ref.set(data)
            return rec_obj
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to cache claim memory record '{rec_obj.cache_id}': {str(e)}"
            ) from e

    def get_by_id(self, cache_id: str) -> Optional[CacheRecord]:
        """
        Retrieves cache record by cache_id.
        """
        try:
            doc_ref = self.collection.document(cache_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            return CacheRecord.model_validate(doc.to_dict())
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to retrieve cache record '{cache_id}': {str(e)}"
            ) from e

    def get_by_hash(self, content_hash: str) -> Optional[CacheRecord]:
        """
        Finds cached dossier by cryptographic SHA-256 hash.
        """
        try:
            docs = self.collection.where("content_hash", "==", content_hash).limit(1).stream()
            for doc in docs:
                return CacheRecord.model_validate(doc.to_dict())
            return None
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to query cache by hash '{content_hash}': {str(e)}"
            ) from e

    def increment_hit_count(self, cache_id: str) -> Optional[CacheRecord]:
        """
        Increments the hit counter and updates last accessed timestamp.
        """
        rec = self.get_by_id(cache_id)
        if not rec:
            return None

        new_count = rec.hit_count + 1
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            doc_ref = self.collection.document(cache_id)
            doc_ref.update({
                "hit_count": new_count,
                "last_accessed_at": now_iso,
            })
            rec.hit_count = new_count
            return rec
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to increment hit count for cache '{cache_id}': {str(e)}"
            ) from e

    def delete_record(self, cache_id: str) -> bool:
        """
        Deletes a cached memory record by ID.
        """
        try:
            doc_ref = self.collection.document(cache_id)
            doc_ref.delete()
            return True
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to delete cache record '{cache_id}': {str(e)}"
            ) from e
