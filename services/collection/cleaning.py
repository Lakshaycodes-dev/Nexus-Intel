"""HTML/text cleaning, deterministic table parsing and normalisation helpers."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import date, datetime
from html import unescape
from html.parser import HTMLParser
from typing import Any, Iterable, Optional

_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript|svg|template)\b[^>]*>.*?</\1>",
    re.IGNORECASE | re.DOTALL,
)
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)
_BLOCK_TAG_RE = re.compile(
    r"</?(?:p|div|section|article|header|footer|main|aside|nav|li|ul|ol|tr|td|th|"
    r"table|thead|tbody|h[1-6]|br|hr|form|label|button|option|select|dt|dd|"
    r"figure|figcaption|blockquote|pre|address)\b[^>]*>",
    re.IGNORECASE,
)
_ANY_TAG_RE = re.compile(r"<[^>]+>")
_MULTISPACE_RE = re.compile(r"[ \t\u00a0]+")
_MULTINEWLINE_RE = re.compile(r"\n{3,}")

_VOLATILE_PATTERNS = (
    re.compile(r"\b\d{2}:\d{2}(?::\d{2})?\s*(?:am|pm|utc|gmt)?\b", re.IGNORECASE),
    re.compile(r"\b\d{4}-\d{2}-\d{2}t\d{2}:\d{2}:\d{2}(?:\.\d+)?z?\b", re.IGNORECASE),
    re.compile(r"\b(?:session|request|trace|build|nonce|csrf)[-_]?\w{6,}\b", re.IGNORECASE),
    re.compile(r"\b[0-9a-f]{16,}\b", re.IGNORECASE),
    re.compile(r"\bnanoid[-_]\w+\b", re.IGNORECASE),
)

_PRICE_RE = re.compile(
    r"(?P<currency>[$€£¥₹]|USD|EUR|GBP|JPY|INR|CAD|AUD|CHF)?\s*"
    r"(?P<amount>\d[\d,_]*(?:\.\d+)?)\s*(?P<suffix>[kKmM])?",
)
_CURRENCY_SYMBOLS = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR"}
_DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y/%m/%d",
    "%B %d, %Y",
    "%b %d, %Y",
    "%d %B %Y",
    "%d %b %Y",
    "%m/%d/%Y",
    "%d/%m/%Y",
)
_MONTHS = (
    "january", "february", "march", "april", "may", "june", "july",
    "august", "september", "october", "november", "december",
)
_DATE_TEXT_RE = re.compile(
    r"\b(?:%s)\s+\d{1,2},?\s+\d{4}\b|\b\d{1,2}\s+(?:%s)\s+\d{4}\b|\b\d{4}-\d{2}-\d{2}\b"
    % ("|".join(_MONTHS), "|".join(_MONTHS)),
    re.IGNORECASE,
)


def html_to_text(html: str) -> str:
    """Convert rendered HTML into readable text while preserving structure."""
    if not html:
        return ""
    text = _COMMENT_RE.sub(" ", html)
    text = _SCRIPT_STYLE_RE.sub(" ", text)
    text = _BLOCK_TAG_RE.sub("\n", text)
    text = _ANY_TAG_RE.sub(" ", text)
    text = unescape(text)
    return clean_text(text)


def clean_text(text: Optional[str]) -> str:
    """Normalise unicode/whitespace without destroying line structure."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKC", str(text))
    normalized = normalized.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    normalized = _MULTISPACE_RE.sub(" ", normalized)
    normalized = "\n".join(line.strip() for line in normalized.split("\n"))
    normalized = _MULTINEWLINE_RE.sub("\n\n", normalized)
    return normalized.strip()


def clean_html(html: str) -> str:
    """Strip executable/style markup and cap size before persistence."""
    if not html:
        return ""
    cleaned = _COMMENT_RE.sub("", html)
    cleaned = _SCRIPT_STYLE_RE.sub("", cleaned)
    cleaned = re.sub(r"\s+on\w+\s*=\s*\"[^\"]*\"", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+on\w+\s*=\s*'[^']*'", "", cleaned, flags=re.IGNORECASE)
    return cleaned


def stable_text(text: str) -> str:
    """Return text with volatile timestamps/ids removed, used for hashing."""
    value = clean_text(text).lower()
    for pattern in _VOLATILE_PATTERNS:
        value = pattern.sub(" ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def content_hash(*parts: str) -> str:
    digest = hashlib.sha256()
    for part in parts:
        digest.update((part or "").encode("utf-8", errors="ignore"))
        digest.update(b"\x1f")
    return digest.hexdigest()


def text_hash(text: str) -> str:
    return content_hash(stable_text(text))


def dedupe_preserve_order(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        key = value.strip()
        if key and key not in seen:
            seen.add(key)
            result.append(key)
    return result


def normalize_currency(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text in _CURRENCY_SYMBOLS:
        return _CURRENCY_SYMBOLS[text]
    if len(text) <= 3 and text.isalpha():
        return text.upper()
    return None


def parse_price(value: Any) -> Optional[dict[str, Any]]:
    """Parse the first monetary value, preserving the original display text."""
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {"amount": float(value), "currency": None, "display": str(value)}
    raw = str(value).strip()
    if not raw or re.search(r"\b(contact|sales|custom|quote|call us)\b", raw, re.IGNORECASE):
        return None
    match = _PRICE_RE.search(raw)
    if not match:
        return None
    try:
        amount = float(match.group("amount").replace(",", "").replace("_", ""))
    except ValueError:
        return None
    suffix = (match.group("suffix") or "").lower()
    if suffix == "k":
        amount *= 1_000
    elif suffix == "m":
        amount *= 1_000_000
    currency = match.group("currency")
    return {
        "amount": amount,
        "currency": normalize_currency(currency),
        "display": raw,
    }


def normalize_billing_period(text: str, *, billing_state: str = "default") -> str:
    lowered = (text or "").lower()
    if re.search(r"/\s*(?:mo(?:nth)?|monthly)\b|per\s+month\b|monthly\b", lowered):
        if re.search(r"billed\s+annual|annual.*(?:/mo|per month)|per month.*annual", lowered):
            return "yearly"
        return "monthly"
    if re.search(r"/\s*(?:yr|year)\b|per\s+year\b|annually\b|yearly\b|annual\b", lowered):
        return "yearly"
    if re.search(r"per\s+(?:hour|hr)\b|hourly\b", lowered):
        return "hourly"
    if re.search(r"per\s+(?:day)\b|daily\b", lowered):
        return "daily"
    if re.search(r"one[-\s]?time|one[-\s]?off", lowered):
        return "one_time"
    if re.search(r"per\s+(?:1m|million)?\s*token|per\s+token", lowered):
        return "per_token"
    if re.search(r"per\s+(?:1k|request)|per\s+request", lowered):
        return "per_request"
    if re.search(r"usage|metered|pay\s+as\s+you\s+go", lowered):
        return "usage"
    if billing_state == "annual":
        return "yearly"
    if billing_state == "monthly":
        return "monthly"
    return "other"


def normalize_date(value: Any) -> tuple[Optional[str], Optional[str]]:
    """Return ``(iso_date, raw_text)``; never discards an unparsed date."""
    if value is None:
        return None, None
    if isinstance(value, datetime):
        return value.date().isoformat(), value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat(), value.isoformat()
    raw = str(value).strip()
    if not raw:
        return None, None
    iso_match = re.match(r"(\d{4}-\d{2}-\d{2})", raw)
    if iso_match:
        return iso_match.group(1), raw
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date().isoformat(), raw
        except ValueError:
            continue
    return None, raw


def find_date(text: str) -> tuple[Optional[str], Optional[str]]:
    match = _DATE_TEXT_RE.search(text or "")
    if not match:
        return None, None
    return normalize_date(match.group(0))


def first_paragraphs(text: str, limit: int = 3, max_chars: int = 900) -> str:
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text or "") if len(p.strip()) > 40]
    joined = "\n\n".join(paragraphs[:limit])
    return joined[:max_chars]


class _TableParser(HTMLParser):
    """Small, dependency-free table extractor with rowspan/colspan expansion."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table_stack: list[list[list[str]]] = []
        self._row: Optional[list[str]] = None
        self._cell: Optional[list[str]] = None
        self._in_table = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        tag = tag.lower()
        if tag == "table":
            self._in_table = True
            self._table_stack.append([])
        elif tag == "tr" and self._in_table and self._table_stack:
            self._row = []
        elif tag in {"td", "th"} and self._in_table and self._row is not None:
            self._cell = []
        elif tag == "br" and self._cell is not None:
            self._cell.append(" ")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"td", "th"} and self._cell is not None and self._row is not None:
            self._row.append(clean_text("".join(self._cell)))
            self._cell = None
        elif tag == "tr" and self._row is not None and self._table_stack:
            if any(cell for cell in self._row):
                self._table_stack[-1].append(self._row)
            self._row = None
        elif tag == "table" and self._table_stack:
            table = self._table_stack.pop()
            if table:
                self.tables.append(table)
            self._in_table = bool(self._table_stack)

    def handle_data(self, data: str) -> None:
        if self._cell is not None:
            self._cell.append(data)


def parse_html_tables(html: str, *, max_tables: int = 25, max_rows: int = 400) -> list[dict[str, Any]]:
    """Return ``[{"headers": [...], "rows": [[...], ...]}]`` from HTML."""
    if not html:
        return []
    parser = _TableParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception:
        return []
    tables: list[dict[str, Any]] = []
    for raw in parser.tables[:max_tables]:
        rows = [row for row in raw if any(cell for cell in row)][:max_rows]
        if not rows:
            continue
        headers = rows[0] if len(rows) > 1 else []
        body = rows[1:] if len(rows) > 1 else rows
        tables.append({"headers": headers, "rows": body})
    return tables


def extract_headings(html: str, *, limit: int = 80) -> list[str]:
    if not html:
        return []
    pattern = re.compile(r"<h[1-6]\b[^>]*>(.*?)</h[1-6]>", re.IGNORECASE | re.DOTALL)
    headings = [html_to_text(match) for match in pattern.findall(html)]
    return [h for h in dedupe_preserve_order(headings) if h][:limit]


def extract_meta_description(html: str) -> str:
    match = re.search(
        r"<meta\b[^>]*name=[\"']description[\"'][^>]*content=[\"'](.*?)[\"']",
        html or "",
        re.IGNORECASE | re.DOTALL,
    )
    if not match:
        match = re.search(
            r"<meta\b[^>]*content=[\"'](.*?)[\"'][^>]*name=[\"']description[\"']",
            html or "",
            re.IGNORECASE | re.DOTALL,
        )
    return clean_text(unescape(match.group(1))) if match else ""


def truncate(text: str, max_chars: int) -> tuple[str, bool]:
    if len(text) <= max_chars:
        return text, False
    cut = text.rfind("\n", 0, max_chars)
    if cut < max_chars // 2:
        cut = max_chars
    return text[:cut].rstrip(), True
