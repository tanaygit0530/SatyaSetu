from typing import Any, Dict, List, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import Source


class SourceRepository(BaseFirestoreRepository):
    """Repository handling official government registry sources."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.SOURCES, db=db)

    def save_source(self, source: Union[Source, Dict[str, Any]]) -> Source:
        src_obj = source if isinstance(source, Source) else Source.model_validate(source)
        data = self.serialize_model(src_obj)
        try:
            doc_ref = self.collection.document(src_obj.source_id)
            doc_ref.set(data)
            return src_obj
        except Exception as e:
            raise DatabaseOperationError(f"Failed to save source '{src_obj.source_id}': {str(e)}") from e

    def get_source(self, source_id: str) -> Optional[Source]:
        try:
            doc_ref = self.collection.document(source_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            return Source.model_validate(doc.to_dict())
        except Exception as e:
            raise DatabaseOperationError(f"Failed to retrieve source '{source_id}': {str(e)}") from e

    def list_sources(self, tier: Optional[int] = None, limit: int = 100) -> List[Source]:
        try:
            query = self.collection
            if tier is not None:
                query = query.where("source_tier", "==", tier)
            docs = query.limit(limit).stream()
            results: List[Source] = []
            for doc in docs:
                results.append(Source.model_validate(doc.to_dict()))
            return results
        except Exception as e:
            raise DatabaseOperationError(f"Failed to list sources: {str(e)}") from e
