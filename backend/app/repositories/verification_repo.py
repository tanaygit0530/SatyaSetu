from typing import Dict, Optional
from app.schemas.verification import VerificationResponse
from app.core.config import settings
from app.core.logging import logger


class VerificationRepository:
    """
    Repository for persisting and retrieving verification dossiers.
    Supports in-memory storage (zero infra dependency) and Cloud Firestore when configured.
    """

    def __init__(self):
        self._memory_store: Dict[str, VerificationResponse] = {}
        self._firestore_client = None

        if settings.FIREBASE_CREDENTIALS_PATH or settings.FIREBASE_PROJECT_ID:
            try:
                import firebase_admin
                from firebase_admin import credentials, firestore

                if not firebase_admin._apps:
                    if settings.FIREBASE_CREDENTIALS_PATH:
                        cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
                        firebase_admin.initialize_app(cred)
                    else:
                        firebase_admin.initialize_app()
                self._firestore_client = firestore.client()
                logger.info("Connected to Cloud Firestore for verification dossier storage.")
            except Exception as e:
                logger.warning("Firebase initialization skipped: %s. Using in-memory repository.", str(e))

    def save(self, record: VerificationResponse) -> None:
        """Saves a verification dossier."""
        self._memory_store[record.id] = record
        if self._firestore_client:
            try:
                doc_ref = self._firestore_client.collection("verification_checks").document(record.id)
                doc_ref.set(record.model_dump(mode="json"))
            except Exception as e:
                logger.error("Failed to write to Cloud Firestore: %s", str(e))

    def get_by_id(self, check_id: str) -> Optional[VerificationResponse]:
        """Retrieves a verification dossier by check ID."""
        if check_id in self._memory_store:
            return self._memory_store[check_id]

        if self._firestore_client:
            try:
                doc = self._firestore_client.collection("verification_checks").document(check_id).get()
                if doc.exists:
                    data = doc.to_dict()
                    return VerificationResponse.model_validate(data)
            except Exception as e:
                logger.error("Failed to read from Cloud Firestore: %s", str(e))

        return None


verification_repo = VerificationRepository()
