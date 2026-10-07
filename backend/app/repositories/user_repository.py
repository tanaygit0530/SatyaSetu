from typing import Any, Dict, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import User


class UserRepository(BaseFirestoreRepository):
    """Repository handling user profiles and authorization roles."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.USERS, db=db)

    def save_user(self, user: Union[User, Dict[str, Any]]) -> User:
        user_obj = user if isinstance(user, User) else User.model_validate(user)
        data = self.serialize_model(user_obj)
        try:
            doc_ref = self.collection.document(user_obj.user_id)
            doc_ref.set(data)
            return user_obj
        except Exception as e:
            raise DatabaseOperationError(f"Failed to save user '{user_obj.user_id}': {str(e)}") from e

    def get_user(self, user_id: str) -> Optional[User]:
        try:
            doc_ref = self.collection.document(user_id)
            doc = doc_ref.get()
            if not doc.exists:
                return None
            return User.model_validate(doc.to_dict())
        except Exception as e:
            raise DatabaseOperationError(f"Failed to retrieve user '{user_id}': {str(e)}") from e
