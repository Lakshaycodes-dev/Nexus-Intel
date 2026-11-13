"""URL normalisation, same-site filtering and SSRF protection.

The safeguards here are intentionally conservative:

* only ``http``/``https`` URLs are accepted;
* userinfo in URLs is rejected;
* loopback, private, link-local, reserved, multicast and unspecified IP ranges
  are rejected;
* cloud metadata endpoints are rejected explicitly;
* DNS is resolved for every navigation target and the resolved addresses are
  validated *before* the browser is allowed to navigate.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
import socket
from html.parser import HTMLParser
from typing import Iterable, Optional
from urllib.parse import (
    parse_qsl,
    quote,
    urlencode,
    urljoin,
    urlsplit,
    urlunsplit,
)

_ALLOWED_SCHEMES = {"http", "https"}

_BLOCKED_HOSTNAMES = frozenset(
    {
        "localhost",
        "ip6-localhost",
        "ip6-loopback",
        "0.0.0.0",
        "broadcasthost",
        "metadata",
        "metadata.google.internal",
        "metadata.goog",
    }
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
    ".metadata",
)
_BLOCKED_LITERAL_IPS = {
    "169.254.169.254",
    "169.254.170.2",
    "100.100.100.200",
    "fd00::1",
}

_TRACKING_PARAM_PREFIXES = (
    "utm_",
    "mc_",
    "ref",
    "referrer",
    "source",
    "src",
    "fbclid",
    "gclid",
    "yclid",
    "msclkid",
    "igshid",
    "spm",
    "_ga",
    "_gl",
    "wickedid",
    "oly_enc_id",
    "vero_id",
    "campaign",
)
_TRACKING_PARAMS = frozenset({"ref", "referrer", "source", "src", "campaign"})

_BAD_EXTENSIONS = (
    ".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".css", ".js",
    ".json", ".xml", ".txt", ".pdf", ".zip", ".gz", ".tar", ".rar", ".7z",
    ".mp4", ".mp3", ".avi", ".mov", ".woff", ".woff2", ".ttf", ".eot",
    ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
)

_DEFAULT_PORTS = {"http": 80, "https": 443}


class UnsafeURLError(ValueError):
    """Raised when a URL is malformed, non-public or otherwise unsafe."""


def _looks_like_url(value: str) -> bool:
    return bool(re.match(r"^https?://", value.strip(), re.IGNORECASE))


def normalize_host(host: Optional[str]) -> str:
    if not host:
        raise UnsafeURLError("URL has no hostname.")
    normalized = host.strip().rstrip(".").lower()
    if not normalized:
        raise UnsafeURLError("URL has no hostname.")
    return normalized


def ensure_http_url(value: str) -> str:
    """Return an absolute http(s) URL, adding ``https://`` when no scheme."""
    if not isinstance(value, str) or not value.strip():
        raise UnsafeURLError("A URL is required.")
    candidate = value.strip()
    if "://" not in candidate:
        candidate = f"https://{candidate}"
    parts = urlsplit(candidate)
    if parts.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeURLError(
            f"Unsupported URL scheme {parts.scheme!r}; only http and https are allowed."
        )
    if not parts.netloc:
        raise UnsafeURLError(f"{value!r} is not an absolute http(s) URL.")
    if parts.username or parts.password:
        raise UnsafeURLError("Credentials embedded in URLs are not allowed.")
    return candidate


def _ip_is_public(address: ipaddress._BaseAddress) -> bool:
    return not (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_reserved
        or address.is_multicast
        or address.is_unspecified
    )


def check_host_syntax(host: str, *, allow_private: bool = False) -> None:
    """Synchronous host/IP validation used for every request."""
    normalized = normalize_host(host)
    if normalized in _BLOCKED_HOSTNAMES or normalized.endswith(_BLOCKED_SUFFIXES):
        raise UnsafeURLError(
            f"Host {normalized!r} resolves to an internal target and is not allowed."
        )
    try:
        address = ipaddress.ip_address(normalized)
    except ValueError:
        address = None
    if address is not None:
        if str(address) in _BLOCKED_LITERAL_IPS:
            raise UnsafeURLError(f"IP address {address} is a blocked endpoint.")
        if not allow_private and not _ip_is_public(address):
            raise UnsafeURLError(
                f"IP address {address} belongs to a private or internal range."
            )
        return
    if "." not in normalized:
        raise UnsafeURLError(f"{normalized!r} is not a fully-qualified public domain.")
    if any(not label or len(label) > 63 for label in normalized.split(".")):
        raise UnsafeURLError(f"{normalized!r} is not a valid domain name.")
    if len(normalized) > 253:
        raise UnsafeURLError("Domain name is too long.")
    try:
        normalized.encode("ascii")
    except UnicodeEncodeError as exc:
        raise UnsafeURLError(
            "Internationalised domain names must use their punycode (xn--) form."
        ) from exc


async def validate_public_url(url: str, *, allow_private: bool = False) -> str:
    """Validate scheme, host syntax and (if not an IP) every resolved address."""
    candidate = ensure_http_url(url)
    parts = urlsplit(candidate)
    host = normalize_host(parts.hostname)
    check_host_syntax(host, allow_private=allow_private)
    try:
        ipaddress.ip_address(host)
        return candidate  # literal IP already validated
    except ValueError:
        pass

    loop = asyncio.get_running_loop()
    try:
        infos = await loop.run_in_executor(
            None,
            lambda: socket.getaddrinfo(host, parts.port or _DEFAULT_PORTS[parts.scheme.lower()], type=socket.SOCK_STREAM),
        )
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Could not resolve host {host!r}: {exc}") from exc
    if not infos:
        raise UnsafeURLError(f"Could not resolve host {host!r}.")
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if str(address) in _BLOCKED_LITERAL_IPS:
            raise UnsafeURLError(f"Host {host!r} resolves to a blocked endpoint.")
        if not allow_private and not _ip_is_public(address):
            raise UnsafeURLError(
                f"Host {host!r} resolves to private/internal address {address}."
            )
    return candidate


def _is_tracking_param(key: str) -> bool:
    lowered = key.lower()
    if lowered in _TRACKING_PARAMS:
        return True
    return any(lowered.startswith(prefix) for prefix in _TRACKING_PARAM_PREFIXES if prefix not in _TRACKING_PARAMS)


def canonicalize_url(
    base: str,
    url: str,
    *,
    strip_fragments: bool = True,
    drop_tracking: bool = True,
    keep_query: bool = False,
) -> Optional[str]:
    """Resolve ``url`` against ``base`` and return a canonical absolute URL.

    Returns ``None`` for non-http(s), asset-like or unparseable links.
    """
    if not url:
        return None
    candidate = url.strip()
    if not candidate or candidate.startswith(("#", "mailto:", "tel:", "javascript:", "data:")):
        return None
    absolute = urljoin(base, candidate)
    try:
        parts = urlsplit(absolute)
    except ValueError:
        return None
    if parts.scheme.lower() not in _ALLOWED_SCHEMES:
        return None
    if parts.username or parts.password:
        return None
    host = normalize_host(parts.hostname)
    port = parts.port
    netloc = host
    if port and port != _DEFAULT_PORTS[parts.scheme.lower()]:
        netloc = f"{host}:{port}"

    path = parts.path or "/"
    path = re.sub(r"/{2,}", "/", path)
    if path.lower().endswith(_BAD_EXTENSIONS):
        return None

    query_pairs: list[tuple[str, str]] = []
    if keep_query:
        for key, value in parse_qsl(parts.query, keep_blank_values=False):
            if drop_tracking and _is_tracking_param(key):
                continue
            query_pairs.append((key, value))
    query_pairs.sort()
    query = urlencode(query_pairs, doseq=True)
    fragment = "" if strip_fragments else parts.fragment
    return urlunsplit((parts.scheme.lower(), netloc, quote(path, safe="/:@!$&'()*+,;=-._~%"), query, fragment))


def site_root(url: str) -> str:
    parts = urlsplit(ensure_http_url(url))
    return f"{parts.scheme.lower()}://{normalize_host(parts.hostname)}"


def is_internal_url(url: str, root_host: str) -> bool:
    try:
        host = normalize_host(urlsplit(url).hostname)
    except UnsafeURLError:
        return False
    root = normalize_host(root_host)
    # Treat ``www`` as equivalent to the bare host so links between
    # ``https://www.example.com`` and ``https://example.com`` stay internal.
    host = host.removeprefix("www.")
    root = root.removeprefix("www.")
    return host == root or host.endswith("." + root)


def host_matches(url: str, root_host: str) -> bool:
    return is_internal_url(url, root_host)


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[str] = []
        self.base: Optional[str] = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        values = dict(attrs)
        if tag.lower() == "base" and values.get("href"):
            self.base = values["href"]
        elif tag.lower() == "a" and values.get("href"):
            self.links.append(values["href"])


def extract_links_from_html(html: str) -> list[str]:
    parser = _LinkParser()
    try:
        parser.feed(html or "")
        parser.close()
    except Exception:
        return []
    if parser.base:
        parser.links = [urljoin(parser.base, link) for link in parser.links]
    return parser.links


_SITEMAP_LOC_RE = re.compile(r"<loc>\s*(.*?)\s*</loc>", re.IGNORECASE | re.DOTALL)
_SITEMAP_URLSET_RE = re.compile(r"<urlset\b", re.IGNORECASE)
_SITEMAP_INDEX_RE = re.compile(r"<sitemapindex\b", re.IGNORECASE)


def parse_sitemap(xml: str) -> tuple[list[str], bool]:
    """Return ``(locations, is_index)`` from a sitemap document."""
    locations = [
        raw.strip()
        for raw in _SITEMAP_LOC_RE.findall(xml or "")
        if raw.strip()
    ]
    # XML escaping is rare in <loc> for normal URLs, but decode common entities.
    locations = [
        loc.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        for loc in locations
    ]
    return locations, bool(_SITEMAP_INDEX_RE.search(xml or ""))


def looks_like_asset(url: str) -> bool:
    try:
        path = urlsplit(url).path.lower()
    except ValueError:
        return True
    return path.endswith(_BAD_EXTENSIONS)


def dedupe_urls(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for url in urls:
        if url and url not in seen:
            seen.add(url)
            result.append(url)
    return result


def clean_text_urls(values: Iterable[str]) -> list[str]:
    """Keep only absolute http(s) URLs (used for resolver results)."""
    results: list[str] = []
    for value in values:
        try:
            results.append(ensure_http_url(value))
        except UnsafeURLError:
            continue
    return dedupe_urls(results)
