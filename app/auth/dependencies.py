"""FastAPI dependencies for authenticated requests."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.database import UserRepository, get_user_repository
from app.errors import UnauthorizedError

from .tokens import decode_token

# ``auto_error=False`` lets us return the API's consistent error envelope
# (401 + {"error": {...}}) instead of FastAPI's bare 403.
_bearer = HTTPBearer(
    auto_error=False,
    description="Access token returned by POST /api/v1/auth/login.",
)


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    """Strip secrets (password hash, Mongo ``_id``) before a user leaves the API."""
    return {
        "user_id": user["user_id"],
        "email": user["email"],
        "name": user.get("name") or "",
        "workspace_name": user.get("workspace_name") or "",
        "created_at": user["created_at"],
    }


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
    users: UserRepository = Depends(get_user_repository),
) -> dict[str, Any]:
    """Resolve the bearer token to a stored user document.

    Raises :class:`UnauthorizedError` for a missing/expired token or a user that
    no longer exists, so every protected route fails closed.
    """
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Sign in to continue.")

    claims = decode_token(credentials.credentials)
    if claims is None:
        raise UnauthorizedError("Your session has expired. Please sign in again.")

    user = await users.get_by_id(claims["sub"])
    if user is None:
        raise UnauthorizedError("Your session is no longer valid. Please sign in again.")
    return user
