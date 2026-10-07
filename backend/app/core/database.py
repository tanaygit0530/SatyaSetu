import json
import os
from typing import Optional
from app.core.config import settings
from app.core.exceptions import FirebaseConfigurationError
from app.core.logging import logger

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    firebase_admin = None
    credentials = None
    firestore = None


class FirestoreCollections:
    """The 10 canonical Cloud Firestore collections for SachCheck."""
    USERS = "users"
    CHECKS = "checks"
    CLAIMS = "claims"
    EVIDENCE = "evidence"
    FEEDBACK = "feedback"
    SOURCES = "sources"
    CLAIM_MEMORY = "claim_memory"
    REVIEW_QUEUE = "review_queue"
    METRICS = "metrics"
    EVALUATION_RUNS = "evaluation_runs"


_cached_firestore_client: Optional[object] = None


def get_firestore_client():
    """
    Returns an authenticated Cloud Firestore client instance.
    Raises FirebaseConfigurationError if Firebase Admin is not installed or
    credentials / project settings are missing.
    """
    global _cached_firestore_client

    if _cached_firestore_client is not None:
        return _cached_firestore_client

    if not FIREBASE_AVAILABLE:
        raise FirebaseConfigurationError(
            "Firebase Admin SDK is not installed. Please install firebase-admin."
        )

    # Check for emulator host override
    if settings.FIRESTORE_EMULATOR_HOST:
        os.environ["FIRESTORE_EMULATOR_HOST"] = settings.FIRESTORE_EMULATOR_HOST

    # Validate that at least one credential or project configuration is present
    has_cred_path = bool(settings.FIREBASE_CREDENTIALS_PATH and os.path.exists(settings.FIREBASE_CREDENTIALS_PATH))
    has_cred_json = bool(settings.FIREBASE_CREDENTIALS_JSON)
    has_project_id = bool(settings.FIREBASE_PROJECT_ID)

    if not (has_cred_path or has_cred_json or has_project_id):
        raise FirebaseConfigurationError(
            "Firebase is unavailable: Neither FIREBASE_CREDENTIALS_PATH, "
            "FIREBASE_CREDENTIALS_JSON, nor FIREBASE_PROJECT_ID are configured in environment."
        )

    try:
        if not firebase_admin._apps:
            cred_obj = None
            if settings.FIREBASE_CREDENTIALS_PATH:
                if not os.path.exists(settings.FIREBASE_CREDENTIALS_PATH):
                    raise FirebaseConfigurationError(
                        f"Firebase credentials file not found at: {settings.FIREBASE_CREDENTIALS_PATH}"
                    )
                cred_obj = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            elif settings.FIREBASE_CREDENTIALS_JSON:
                try:
                    cred_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
                    cred_obj = credentials.Certificate(cred_dict)
                except Exception as json_err:
                    raise FirebaseConfigurationError(
                        f"Failed to parse FIREBASE_CREDENTIALS_JSON: {json_err}"
                    )
            elif settings.FIREBASE_PROJECT_ID:
                cred_obj = credentials.ApplicationDefault()

            app_options = {}
            if settings.FIREBASE_PROJECT_ID:
                app_options["projectId"] = settings.FIREBASE_PROJECT_ID

            firebase_admin.initialize_app(cred_obj, app_options if app_options else None)
            logger.info("Firebase Admin initialized successfully.")

        database_id = settings.FIRESTORE_DATABASE_ID or "(default)"
        if database_id and database_id != "(default)":
            client = firestore.client(database=database_id)
        else:
            client = firestore.client()

        _cached_firestore_client = client
        return _cached_firestore_client

    except FirebaseConfigurationError:
        raise
    except Exception as e:
        raise FirebaseConfigurationError(
            f"Failed to initialize Cloud Firestore client: {str(e)}"
        ) from e


def set_firestore_client(client: Optional[object]) -> None:
    """Explicitly inject or mock the Firestore client (used for testing)."""
    global _cached_firestore_client
    _cached_firestore_client = client


def reset_firestore_client() -> None:
    """Clears the cached Firestore client."""
    global _cached_firestore_client
    _cached_firestore_client = None
