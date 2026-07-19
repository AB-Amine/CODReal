"""JWT auth via Supabase access tokens."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.supabase_client import is_supabase_configured

_bearer = HTTPBearer(auto_error=False)


@dataclass
class AuthUser:
    id: str
    email: str | None = None
    role: str = "authenticated"


def _user_from_supabase_api(token: str) -> AuthUser:
    """Validate access token via Supabase Auth (works with HS256 and new signing keys)."""
    if not is_supabase_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Supabase non configuré (SUPABASE_URL + SUPABASE_KEY)",
        )
    from app.core.supabase_client import get_supabase_admin

    try:
        resp = get_supabase_admin().auth.get_user(token)
        user = resp.user
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token invalide (utilisateur introuvable)",
            )
        return AuthUser(id=str(user.id), email=getattr(user, "email", None))
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token rejeté par Supabase Auth: {exc}",
        ) from exc


def _user_from_local_jwt(token: str) -> AuthUser | None:
    """Try HS256 decode with JWT secret (legacy). Returns None if not applicable."""
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
            # Some projects omit / change aud; still require signature
            payload = jwt.decode(
                token,
                secret,
                algorithms=["HS256"],
                options={"verify_aud": False},
            )
        except JWTError:
            return None

    sub = payload.get("sub")
    if not sub:
        return None
    return AuthUser(
        id=str(sub),
        email=payload.get("email"),
        role=str(payload.get("role") or "authenticated"),
    )


def _decode_supabase_jwt(token: str) -> AuthUser:
    token = (token or "").strip()
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token vide",
        )

    # 1) Prefer local JWT if secret works (fast, offline)
    local = _user_from_local_jwt(token)
    if local:
        return local

    # 2) Always fall back to Supabase Auth API (reliable with current projects)
    return _user_from_supabase_api(token)


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
    return _decode_supabase_jwt(credentials.credentials)


async def get_optional_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer)
    ] = None,
) -> AuthUser | None:
    if credentials is None or not credentials.credentials:
        return None
    # Do not swallow invalid tokens silently when a header was sent
    return _decode_supabase_jwt(credentials.credentials)


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
OptionalUser = Annotated[AuthUser | None, Depends(get_optional_user)]
