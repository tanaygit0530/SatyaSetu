from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError, FirebaseConfigurationError
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import CacheRecord
from app.schemas.claim_memory import ClaimMemoryRecord
from app.core.logging import logger


class ClaimMemoryRepository(BaseFirestoreRepository):
    """Repository handling rumour memory and deduplication cache."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.CLAIM_MEMORY, db=db)
        # In-memory local fallback store for seamless operation when Cloud Firestore is offline
        self._local_records: Dict[str, ClaimMemoryRecord] = {}

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

    def get_by_id(self, cache_id: str) -> Optional[Union[CacheRecord, ClaimMemoryRecord]]:
        """
        Retrieves cache record by cache_id.
        """
        if cache_id in self._local_records:
            return self._local_records[cache_id]

        try:
            doc_ref = self.collection.document(cache_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            data = doc.to_dict()
            if "normalized_claim" in data:
                return ClaimMemoryRecord.model_validate(data)
            return CacheRecord.model_validate(data)
        except Exception as e:
            if self._db is not None:
                raise DatabaseOperationError(
                    f"Failed to retrieve cache record '{cache_id}': {str(e)}"
                ) from e
            return None

    def get_by_hash(self, content_hash: str) -> Optional[Union[CacheRecord, ClaimMemoryRecord]]:
        """
        Finds cached dossier by cryptographic SHA-256 hash.
        """
        for r in self._local_records.values():
            if getattr(r, "claim_hash", None) == content_hash or getattr(r, "content_hash", None) == content_hash:
                return r

        try:
            docs = self.collection.where("content_hash", "==", content_hash).limit(1).stream()
            for doc in docs:
                return CacheRecord.model_validate(doc.to_dict())
            return None
        except Exception as e:
            if self._db is not None:
                raise DatabaseOperationError(
                    f"Failed to query cache by hash '{content_hash}': {str(e)}"
                ) from e
            return None

    def increment_hit_count(self, cache_id: str) -> Optional[Union[CacheRecord, ClaimMemoryRecord]]:
        """
        Increments the hit counter and updates last accessed timestamp.
        """
        if cache_id in self._local_records:
            rec = self._local_records[cache_id]
            rec.hit_count += 1
            rec.last_accessed_at = datetime.now(timezone.utc)
            if self._db is not None:
                try:
                    self.collection.document(cache_id).update({
                        "hit_count": rec.hit_count,
                        "last_accessed_at": rec.last_accessed_at.isoformat(),
                    })
                except Exception:
                    pass
            return rec

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
            if self._db is not None:
                raise DatabaseOperationError(
                    f"Failed to increment hit count for cache '{cache_id}': {str(e)}"
                ) from e
            rec.hit_count = new_count
            return rec

    def delete_record(self, cache_id: str) -> bool:
        """
        Deletes a cached memory record by ID.
        """
        self._local_records.pop(cache_id, None)
        try:
            doc_ref = self.collection.document(cache_id)
            doc_ref.delete()
            return True
        except Exception as e:
            # If firestore client is mock or configured, propagate; else succeed locally
            if self._db is not None:
                raise DatabaseOperationError(
                    f"Failed to delete cache record '{cache_id}': {str(e)}"
                ) from e
            return True

    def save_memory_record(self, record: Union[ClaimMemoryRecord, Dict[str, Any]]) -> ClaimMemoryRecord:
        """
        Saves a Shared Claim Memory record into persistent Firestore and local cache.
        """
        rec_obj = record if isinstance(record, ClaimMemoryRecord) else ClaimMemoryRecord.model_validate(record)
        if not rec_obj.cache_id:
            rec_obj.cache_id = f"cch_{rec_obj.claim_hash[:16]}"
        self._local_records[rec_obj.cache_id] = rec_obj
        self._local_records[rec_obj.claim_hash] = rec_obj

        try:
            data = self.serialize_model(rec_obj)
            doc_ref = self.collection.document(rec_obj.cache_id)
            doc_ref.set(data)
            return rec_obj
        except Exception as e:
            if self._db is not None:
                raise DatabaseOperationError(
                    f"Failed to persist claim memory '{rec_obj.cache_id}': {str(e)}"
                ) from e
            logger.info("Saved claim memory record locally: %s", rec_obj.cache_id)
            return rec_obj

    def get_by_claim_hash(self, claim_hash: str) -> Optional[ClaimMemoryRecord]:
        """
        Retrieves a Shared Claim Memory record by cryptographic claim hash.
        """
        if claim_hash in self._local_records:
            return self._local_records[claim_hash]

        try:
            docs = self.collection.where("claim_hash", "==", claim_hash).limit(1).stream()
            for doc in docs:
                rec = ClaimMemoryRecord.model_validate(doc.to_dict())
                self._local_records[claim_hash] = rec
                return rec
            return None
        except Exception as e:
            if self._db is not None:
                raise DatabaseOperationError(
                    f"Failed to query claim memory by hash '{claim_hash}': {str(e)}"
                ) from e
            return None

    def list_all_records(self, limit: int = 500) -> List[ClaimMemoryRecord]:
        """
        Returns all candidate records for semantic similarity scanning.
        """
        records_dict = {r.cache_id: r for r in self._local_records.values()}
        try:
            docs = self.collection.limit(limit).stream()
            for doc in docs:
                data = doc.to_dict()
                if "embedding" in data and "claim_hash" in data:
                    r = ClaimMemoryRecord.model_validate(data)
                    records_dict[r.cache_id] = r
        except Exception:
            pass

        return list(records_dict.values())

