"""Password hashing with the stdlib scrypt KDF.

Hashes are stored as ``scrypt$n$r$p$<salt-b64>$<hash-b64>`` so parameters can
be rotated later without invalidating existing accounts (old hashes keep the
parameters they were created with).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

_SCHEME = "scrypt"
# ~16 MiB of memory and roughly 50-80 ms per hash on commodity hardware.
_N = 2**14
_R = 8
_P = 1
_DKLEN = 32
_SALT_BYTES = 16


def _b64encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).decode("ascii").rstrip("=")


def _b64decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str) -> str:
    """Return a salted scrypt hash for ``password``."""
    salt = secrets.token_bytes(_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_N,
        r=_R,
        p=_P,
        dklen=_DKLEN,
    )
    return f"{_SCHEME}${_N}${_R}${_P}${_b64encode(salt)}${_b64encode(derived)}"


def verify_password(password: str, stored: str | None) -> bool:
    """Constant-time check of ``password`` against a stored hash."""
    if not stored:
        return False
    try:
        scheme, n_raw, r_raw, p_raw, salt_raw, hash_raw = stored.split("$")
        if scheme != _SCHEME:
            return False
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_b64decode(salt_raw),
            n=int(n_raw),
            r=int(r_raw),
            p=int(p_raw),
            dklen=len(_b64decode(hash_raw)),
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived, _b64decode(hash_raw))
