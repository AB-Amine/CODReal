"""Firebase Admin SDK initialization and Cloud Firestore client helper."""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from typing import Any

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class FirebaseNotConfiguredError(RuntimeError):
    """Raised when Firebase credentials are not provided."""


def is_firebase_configured() -> bool:
    """Check if Firebase configuration exists."""
    settings = get_settings()
    return bool(settings.firebase_ready)


@lru_cache
def get_firebase_app() -> Any:
    """Initialize Firebase Admin App once."""
    if not is_firebase_configured():
        raise FirebaseNotConfiguredError(
            "Firebase non configuré. Définissez FIREBASE_PROJECT_ID et "
            "FIREBASE_CLIENT_EMAIL / FIREBASE_PRIVATE_KEY dans .env"
        )
    import firebase_admin
    from firebase_admin import credentials

    if firebase_admin._apps:
        return firebase_admin.get_app()

    settings = get_settings()

    if settings.firebase_credentials_json:
        try:
            cred_dict = json.loads(settings.firebase_credentials_json)
            cred = credentials.Certificate(cred_dict)
        except Exception:
            cred = credentials.Certificate(settings.firebase_credentials_json)
    elif settings.firebase_client_email and settings.firebase_private_key:
        private_key = settings.firebase_private_key.replace("\\n", "\n")
        cred_dict = {
            "type": "service_account",
            "project_id": settings.firebase_project_id,
            "client_email": settings.firebase_client_email,
            "private_key": private_key,
        }
        cred = credentials.Certificate(cred_dict)
    else:
        cred = credentials.ApplicationDefault()

    return firebase_admin.initialize_app(
        cred,
        options={"projectId": settings.firebase_project_id} if settings.firebase_project_id else None,
    )


def get_firestore_admin() -> Any:
    """Get Cloud Firestore client."""
    get_firebase_app()
    from firebase_admin import firestore

    return firestore.client()


def clear_firebase_cache() -> None:
    get_firebase_app.cache_clear()
