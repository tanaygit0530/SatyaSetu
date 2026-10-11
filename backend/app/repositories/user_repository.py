import json
import os
from typing import Any, Dict, Optional, Union
from app.core.database import FirestoreCollections
from app.core.exceptions import DatabaseOperationError
from app.repositories.base import BaseFirestoreRepository
from app.schemas.core import User
from app.core.logging import logger


class UserRepository(BaseFirestoreRepository):
    """Repository handling user profiles and authorization roles."""

    def __init__(self, db: Optional[Any] = None):
        super().__init__(collection_name=FirestoreCollections.USERS, db=db)
        self._local_users: Dict[str, User] = {}
        self._cache_file = os.path.join(os.path.dirname(__file__), "..", "..", ".local_users.json")
        self._load_local_cache()

    def _load_local_cache(self) -> None:
        try:
            if os.path.exists(self._cache_file):
                with open(self._cache_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for uid, udata in data.items():
                        user_obj = User.model_validate(udata)
                        self._local_users[uid] = user_obj
                        if user_obj.phone_number:
                            self._local_users[user_obj.phone_number] = user_obj
        except Exception as e:
            logger.debug("Could not load local users cache: %s", e)

    def _save_local_cache(self) -> None:
        try:
            data = {}
            for k, u in self._local_users.items():
                if k == u.user_id:
                    data[u.user_id] = u.model_dump(mode="json")
            with open(self._cache_file, "w", encoding="utf-8") as f:
                json.dump(data, f, default=str)
        except Exception as e:
            logger.debug("Could not write local users cache: %s", e)

    def save_user(self, user: Union[User, Dict[str, Any]]) -> User:
        user_obj = user if isinstance(user, User) else User.model_validate(user)
        self._local_users[user_obj.user_id] = user_obj
        if user_obj.phone_number:
            self._local_users[user_obj.phone_number] = user_obj
        self._save_local_cache()

        if self.collection is not None:
            try:
                data = self.serialize_model(user_obj)
                doc_ref = self.collection.document(user_obj.user_id)
                doc_ref.set(data)
                return user_obj
            except Exception as e:
                if self._db is not None:
                    raise DatabaseOperationError(f"Failed to save user '{user_obj.user_id}': {str(e)}") from e
                logger.debug("Firestore save skipped/failed, saved user locally: %s", user_obj.user_id)
        return user_obj

    def get_user(self, user_id: str) -> Optional[User]:
        if user_id in self._local_users:
            return self._local_users[user_id]

        if self.collection is not None:
            try:
                doc_ref = self.collection.document(user_id)
                doc = doc_ref.get()
                if not doc.exists:
                    return None
                u = User.model_validate(doc.to_dict())
                self._local_users[user_id] = u
                if u.phone_number:
                    self._local_users[u.phone_number] = u
                return u
            except Exception as e:
                if self._db is not None:
                    raise DatabaseOperationError(f"Failed to retrieve user '{user_id}': {str(e)}") from e
                return None
        return None

    def get_by_phone(self, phone_number: str) -> Optional[User]:
        if not phone_number:
            return None
        clean_phone = phone_number.strip()
        if clean_phone in self._local_users:
            return self._local_users[clean_phone]

        for u in self._local_users.values():
            if getattr(u, "phone_number", None) == clean_phone:
                return u

        if self.collection is not None:
            try:
                docs = self.collection.where("phone_number", "==", clean_phone).limit(1).stream()
                for doc in docs:
                    u = User.model_validate(doc.to_dict())
                    self._local_users[u.user_id] = u
                    self._local_users[clean_phone] = u
                    return u
            except Exception as e:
                if self._db is not None:
                    raise DatabaseOperationError(f"Failed to retrieve user by phone '{clean_phone}': {str(e)}") from e
                return None
        return None

    def update_phone_number(self, user_id: str, new_phone: str) -> Optional[User]:
        user = self.get_user(user_id)
        if not user:
            return None
        old_phone = user.phone_number
        if old_phone and old_phone in self._local_users:
            self._local_users.pop(old_phone, None)

        user.phone_number = new_phone
        user.phone_verified = True
        # Re-evaluate WhatsApp link: reset because the phone identity changed
        user.whatsapp_linked = False
        user.whatsapp_phone_number = None
        user.whatsapp_linked_at = None
        return self.save_user(user)

    def update_whatsapp_link(
        self,
        user_id: str,
        linked: bool,
        whatsapp_phone: Optional[str] = None,
        linked_at: Optional[Any] = None,
    ) -> Optional[User]:
        user = self.get_user(user_id)
        if not user:
            return None
        user.whatsapp_linked = linked
        user.whatsapp_phone_number = whatsapp_phone if linked else None
        user.whatsapp_linked_at = linked_at if linked else None
        return self.save_user(user)

