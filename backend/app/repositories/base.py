from typing import Any, Dict, Optional
from app.core.database import get_firestore_client
from app.core.exceptions import DatabaseOperationError


class BaseFirestoreRepository:
    """
    Abstract base repository providing Firestore access, collection binding,
    and dependency injection capabilities for testing.
    """

    def __init__(self, collection_name: str, db: Optional[Any] = None):
        self.collection_name = collection_name
        self._db = db

    @property
    def db(self):
        """Returns the injected or initialized Firestore client."""
        if self._db is not None:
            return self._db
        return get_firestore_client()

    @property
    def collection(self):
        """Returns the Firestore CollectionReference."""
        client = self.db
        try:
            return client.collection(self.collection_name)
        except Exception as e:
            raise DatabaseOperationError(
                f"Failed to access collection '{self.collection_name}': {str(e)}"
            ) from e

    def serialize_model(self, model: Any) -> Dict[str, Any]:
        """Serializes Pydantic model or dict to JSON-compatible Firestore dictionary."""
        if hasattr(model, "model_dump"):
            return model.model_dump(mode="json")
        if isinstance(model, dict):
            return model
        raise ValueError(f"Cannot serialize object of type {type(model).__name__}")
