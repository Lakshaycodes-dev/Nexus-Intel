"""HS256 JSON Web Tokens issued by the API (stdlib only).

The implementation is deliberately small and strict: the algorithm is fixed,
the signature is compared in constant time, and expired tokens are rejected.
Only the claims the API needs are written: ``sub`` (user id), ``email``,
``iat``, ``exp`` and ``iss``.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from typing import Any, Optional

from app import config

logger = logging.getLogger("nexus_intel.auth")

_ISSUER = "nexus-intel"
_HEADER = {"alg": "HS256", "typ": "JWT"}

_ephemeral_secret: Optional[str] = None


def _signing_secret() -> str:
    """Return the configured secret, or a process-local fallback in dev.

    Production deployments must set ``JWT_SECRET``; otherwise tokens stop
    working after every restart (and are not shared across workers).
    """
    global _ephemeral_secret
    if config.JWT_SECRET:
        return config.JWT_SECRET
    if _ephemeral_secret is None:
        _ephemeral_secret = secrets.token_urlsafe(48)
        logger.warning(
            "JWT_SECRET is not set; using an ephemeral signing key. "
            "Sessions will be invalidated when the API restarts. "
            "Set JWT_SECRET before deploying."
        )
    return _ephemeral_secret


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def _sign(signing_input: str) -> str:
    digest = hmac.new(
        _signing_secret().encode("utf-8"),
        signing_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    return _b64encode(digest)


def create_access_token(user_id: str, email: str) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)`` for the given user."""
    now = int(time.time())
    expires_in = max(60, config.JWT_EXPIRES_MINUTES * 60)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + expires_in,
        "iss": _ISSUER,
    }
    header_part = _b64encode(json.dumps(_HEADER, separators=(",", ":")).encode("utf-8"))
    payload_part = _b64encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    signing_input = f"{header_part}.{payload_part}"
    return f"{signing_input}.{_sign(signing_input)}", expires_in


def decode_token(token: str) -> Optional[dict[str, Any]]:
    """Validate a token and return its claims, or ``None`` when invalid."""
    if not token or token.count(".") != 2:
        return None
    header_part, payload_part, signature_part = token.split(".")
    signing_input = f"{header_part}.{payload_part}"

    try:
        expected = _sign(signing_input)
        if not hmac.compare_digest(expected, signature_part):
            return None

        header = json.loads(_b64decode(header_part))
        if not isinstance(header, dict) or header.get("alg") != "HS256":
            return None

        payload = json.loads(_b64decode(payload_part))
        if not isinstance(payload, dict):
            return None
    except (ValueError, TypeError, json.JSONDecodeError):
        return None

    if payload.get("iss") != _ISSUER:
        return None
    if not isinstance(payload.get("sub"), str) or not payload["sub"]:
        return None
    try:
        if int(payload.get("exp", 0)) <= int(time.time()):
            return None
    except (TypeError, ValueError):
        return None
    return payload
