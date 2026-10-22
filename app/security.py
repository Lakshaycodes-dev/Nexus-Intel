"""Target validation and SSRF safeguards for user-supplied domains/URLs.

The current pipeline fetches pages through the *remote* TinyFish API rather
than from this server, so the direct SSRF surface is small. Even so, every
domain/URL accepted from API clients is validated here so that:

* malformed input is rejected with a clear 422 before any work starts;
* requests for private, loopback, link-local or otherwise internal addresses
  (e.g. ``http://169.254.169.254/``, ``localhost``, ``*.internal``) are refused.

Normalisation intentionally mirrors the frontend's ``normalizeDomain()``
(strips scheme, ``www.``, path and port, lower-cases) so both sides agree on
the competitor identity used as the MongoDB key.
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

# Hostnames that must never be analysed, plus internal-only TLDs/suffixes.
_BLOCKED_HOSTNAMES = frozenset(
    {"localhost", "ip6-localhost", "ip6-loopback", "0.0.0.0", "broadcasthost"}
)
_BLOCKED_SUFFIXES = (
    ".local",
    ".localhost",
    ".internal",
    ".intranet",
    ".corp",
    ".home",
    ".lan",
    ".localdomain",
)

_ALLOWED_SCHEMES = {"http", "https"}


class TargetValidationError(ValueError):
    """Raised when a domain/URL is malformed or points at an internal target."""


def _hostname_of(value: str) -> str | None:
    """Best-effort hostname extraction; ``value`` may or may not have a scheme."""
    candidate = value.strip()
    if not candidate:
        return None
    if "://" not in candidate:
        candidate = f"//{candidate}"
    try:
        parts = urlsplit(candidate)
    except ValueError:
        return None
    return parts.hostname


def _check_hostname(hostname: str | None) -> str:
    if not hostname:
        raise TargetValidationError("Could not read a hostname from the supplied value.")

    host = hostname.strip().rstrip(".").lower()

    if host in _BLOCKED_HOSTNAMES or host.endswith(_BLOCKED_SUFFIXES):
        raise TargetValidationError(
            f"Host {host!r} resolves to an internal target and is not allowed."
        )

    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None

    if address is not None:
        if (
            address.is_private
            or address.is_loopback
            or address.is_link_local
            or address.is_reserved
            or address.is_multicast
            or address.is_unspecified
        ):
            raise TargetValidationError(
                f"IP address {host!r} belongs to a private or internal range "
                "and is not allowed."
            )
        return str(address)

    if "." not in host:
        raise TargetValidationError(
            f"{host!r} is not a fully-qualified public domain name."
        )
    if any(not label or len(label) > 63 for label in host.split(".")):
        raise TargetValidationError(f"{host!r} is not a valid domain name.")
    if len(host) > 253:
        raise TargetValidationError("Domain name is too long.")
    try:
        host.encode("ascii")
    except UnicodeEncodeError as exc:
        raise TargetValidationError(
            "Internationalised domain names must use their punycode (xn--) form."
        ) from exc
    return host


def normalize_domain(value: str) -> str:
    """Normalise a competitor domain exactly like the frontend does.

    ``https://www.Stripe.com/pricing?ref=1`` -> ``stripe.com``.
    Raises :class:`TargetValidationError` for malformed/internal targets.
    """
    if not isinstance(value, str) or not value.strip():
        raise TargetValidationError("A domain or URL is required.")

    candidate = value.strip()
    if "://" in candidate:
        parts = urlsplit(candidate)
        if parts.scheme.lower() not in _ALLOWED_SCHEMES:
            raise TargetValidationError(
                f"Unsupported URL scheme {parts.scheme!r}; use http or https."
            )
        if parts.username or parts.password:
            raise TargetValidationError("Credentials embedded in URLs are not allowed.")
        host = parts.hostname
    else:
        # Bare domain, possibly followed by a path/port (frontend parity).
        host = _hostname_of(candidate)

    hostname = _check_hostname(host)
    if hostname.startswith("www."):
        hostname = hostname[4:]
    return hostname


def validate_target_url(value: str) -> str:
    """Validate an explicitly supplied page URL (http/https, public host).

    Returns the normalised URL string unchanged apart from whitespace, or
    raises :class:`TargetValidationError`.
    """
    if not isinstance(value, str) or not value.strip():
        raise TargetValidationError("A URL is required.")

    candidate = value.strip()
    parts = urlsplit(candidate)
    if parts.scheme.lower() not in _ALLOWED_SCHEMES or not parts.netloc:
        raise TargetValidationError(
            f"{candidate!r} is not an absolute http(s) URL."
        )
    if parts.username or parts.password:
        raise TargetValidationError("Credentials embedded in URLs are not allowed.")
    _check_hostname(parts.hostname)
    return candidate


def derive_query_from_domain(domain: str) -> str:
    """Build the default pipeline search query for a competitor domain.

    The existing orchestrator is *query*-based (``run_pipeline(query, mock)``);
    for ``stripe.com`` this yields ``stripe pricing`` - the same shape as the
    pipeline's own ``DUMMY_QUERY = "Stripe pricing"``.
    """
    label = domain.split(".")[0] if domain else "competitor"
    return f"{label} pricing".strip()
