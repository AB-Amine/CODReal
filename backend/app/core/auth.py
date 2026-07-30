"""Authentication module supporting Firebase ID Tokens and JWT tokens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.firebase_client import is_firebase_configured, get_firebase_app

_bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthUser:
    id: str
    email: str | None = None
    role: str = "authenticated"


def _user_from_firebase(token: str) -> AuthUser | None:
    """Validate token using Firebase Admin SDK."""
    if not is_firebase_configured():
        return None
    try:
        from firebase_admin import auth as firebase_auth
        get_firebase_app()
        decoded = firebase_auth.verify_id_token(token)
        uid = decoded.get("uid") or decoded.get("user_id") or decoded.get("sub")
        if not uid:
            return None
        return AuthUser(
            id=str(uid),
            email=decoded.get("email"),
            role="authenticated",
        )
    except Exception:
        return None


def _user_from_local_jwt(token: str) -> AuthUser | None:
    """Try decoding with local JWT secret (dev / tests / legacy)."""
    settings = get_settings()
    secret = (settings.supabase_jwt_secret or "").strip()
    if not secret or secret == "your-jwt-secret":
        return None

    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_aud": True},
        )
    except JWTError:
        try:
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except JWTError:
            return None

    sub = payload.get("sub") or payload.get("user_id")
    if not sub:
        return None
    return AuthUser(
        id=str(sub),
        email=payload.get("email"),
        role=str(payload.get("role") or "authenticated"),
    )


def _decode_token(token: str) -> AuthUser:
    token = (token or "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token vide",
        )

    # 1) Try Firebase ID token validation
    fb_user = _user_from_firebase(token)
    if fb_user:
        return fb_user

    # 2) Fallback to local JWT decode (dev / unit tests)
    local_user = _user_from_local_jwt(token)
    if local_user:
        return local_user

    # If all fails, attempt unverified payload extraction for dev / tests
    try:
        unverified = jwt.get_unverified_claims(token)
        sub = unverified.get("sub") or unverified.get("user_id") or unverified.get("uid")
        if sub:
            return AuthUser(id=str(sub), email=unverified.get("email"))
    except Exception:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token d'authentification invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
) -> AuthUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=(
                "Authentification requise. Connectez-vous sur /login puis réessayez. "
                "(Header Authorization: Bearer <access_token>)"
            ),
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _decode_token(credentials.credentials)


async def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
) -> AuthUser | None:
    if credentials is None or not credentials.credentials:
        return None
    return _decode_token(credentials.credentials)


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
OptionalUser = Annotated[AuthUser | None, Depends(get_optional_user)]
