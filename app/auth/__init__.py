"""Email/password authentication primitives for the Nexus-Intel API.

The package is intentionally dependency-free: password hashing uses the
stdlib ``hashlib.scrypt`` KDF and access tokens are HS256 JWTs signed with
``hmac``. Both are standard, auditable primitives, so the API can be deployed
without pulling in a third-party auth library.

Public surface:

* :func:`app.auth.passwords.hash_password`
* :func:`app.auth.passwords.verify_password`
* :func:`app.auth.tokens.create_access_token`
* :func:`app.auth.tokens.decode_token`
* :func:`app.auth.dependencies.get_current_user`
* :func:`app.auth.dependencies.public_user`
"""

from .dependencies import get_current_user, public_user
from .passwords import hash_password, verify_password
from .tokens import create_access_token, decode_token

__all__ = [
    "get_current_user",
    "public_user",
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_token",
]
