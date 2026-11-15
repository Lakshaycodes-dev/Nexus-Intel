"""Email/password authentication: register, login, session probe, logout.

Accounts live in the ``users`` collection (see ``app/database.py``) and store
only a scrypt password hash. Successful registration/login returns a signed
HS256 access token that the client sends as ``Authorization: Bearer <token>``.

The endpoints are intentionally stateless: ``/logout`` exists so clients have a
single place to clear a session, but token invalidation is client-side (tokens
expire on their own). A server-side revocation list is the natural next step if
sessions need to be killable.
"""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, Response, status
from pymongo.errors import PyMongoError

from app import config
from app.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    public_user,
    verify_password,
)
from app.database import UserRepository, get_user_repository, utcnow
from app.errors import (
    ConflictError,
    DatabaseUnavailableError,
    ForbiddenError,
    UnauthorizedError,
)
from app.schemas import AuthResponse, LoginRequest, RegisterRequest, UserPublic

logger = logging.getLogger("nexus_intel.auth")

router = APIRouter(prefix="/auth", tags=["auth"])

# Used to keep failed-login timing similar whether or not the email exists.
_DUMMY_HASH = hash_password("nexus-intel-timing-equaliser")


def _auth_response(user: dict) -> AuthResponse:
    token, expires_in = create_access_token(user["user_id"], user["email"])
    return AuthResponse(
        access_token=token,
        expires_in=expires_in,
        user=UserPublic(**public_user(user)),
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an account",
)
async def register(
    payload: RegisterRequest,
    users: UserRepository = Depends(get_user_repository),
) -> AuthResponse:
    """Create a workspace account and return a signed access token."""
    if not config.ALLOW_REGISTRATION:
        raise ForbiddenError("Account creation is currently disabled.")

    try:
        existing = await users.get_by_email(payload.email)
    except PyMongoError as exc:
        raise DatabaseUnavailableError() from exc

    if existing is not None:
        raise ConflictError("An account with this email already exists.")

    now = utcnow()
    first_name = payload.name.split(" ")[0]
    record = {
        "user_id": uuid.uuid4().hex,
        "email": payload.email,
        "name": payload.name,
        "workspace_name": payload.workspace_name or f"{first_name}'s workspace",
        "password_hash": hash_password(payload.password),
        "created_at": now,
        "updated_at": now,
    }

    try:
        await users.create(record)
    except ConflictError:
        raise
    except PyMongoError as exc:
        raise DatabaseUnavailableError() from exc

    logger.info("Registered account %s", record["user_id"])
    return _auth_response(record)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Sign in with email and password",
)
async def login(
    payload: LoginRequest,
    users: UserRepository = Depends(get_user_repository),
) -> AuthResponse:
    """Verify credentials and return a signed access token."""
    try:
        user = await users.get_by_email(payload.email)
    except PyMongoError as exc:
        raise DatabaseUnavailableError() from exc

    if user is None:
        # Equalise timing with the "wrong password" path.
        verify_password(payload.password, _DUMMY_HASH)
        raise UnauthorizedError("Incorrect email or password.")

    if not verify_password(payload.password, user.get("password_hash")):
        raise UnauthorizedError("Incorrect email or password.")

    return _auth_response(user)


@router.get(
    "/me",
    response_model=UserPublic,
    summary="Return the signed-in account",
)
async def me(user: dict = Depends(get_current_user)) -> UserPublic:
    return UserPublic(**public_user(user))


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Clear the client session",
)
async def logout() -> Response:
    """Stateless logout: the client discards its token."""
    return Response(status_code=status.HTTP_204_NO_CONTENT)
