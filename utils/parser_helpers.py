"""Markdown parsing helpers and heuristic fallback extractors.

Two jobs live here:

1. **Normalisation** - clean raw TinyFish markdown before it is sent to Gemini
   (code fences, NBSP, runaway whitespace, truncation) so the prompt contains
   only signal.
2. **Fallback extraction** - best-effort, pure-Python extractors used when the
   LLM path fails (API outage, malformed JSON after repair attempts). They
   produce schema-shaped ``dict`` payloads that are still validated by Pydantic,
   so a fallback result is never less trustworthy than a model result - it just
   carries more ``missing_fields`` / ``warnings``.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any, Iterator, Optional

__all__ = [
    "MarkdownTable",
    "clean_markdown",
    "truncate_markdown",
    "first_heading",
    "iter_markdown_tables",
    "table_to_records",
    "detect_layout",
    "extract_json_block",
    "sanitize_model_text",
    "parse_number",
    "parse_money",
    "parse_bool_token",
    "split_sentences",
    "score_sentiment_text",
    "fallback_pricing_matrix",
    "fallback_feature_comparison",
    "fallback_market_news",
    "fallback_sentiment_score",
]

_FENCE_RE = re.compile(r"```[a-zA-Z0-9_-]*\n?|```")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*?)\s*#*\s*$", re.MULTILINE)
_TABLE_ROW_RE = re.compile(r"^\s*\|(.+)\|\s*$")
_HORIZONTAL_RULE_RE = re.compile(r"^\s*([-*_])(?:\s*\1){2,}\s*$")
_BULLET_RE = re.compile(r"^\s{0,3}(?:[-*+]|\d+\.)\s+(.*)$")
_LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^\s)]+|/[^\s)]*)\)")
_URL_RE = re.compile(r"https?://[^\s)\"'<>\]]+")
_NUMBER_RE = re.compile(r"-?\d[\d,_]*(?:\.\d+)?")
_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")


# --------------------------------------------------------------------------- #
# Normalisation
# --------------------------------------------------------------------------- #
def clean_markdown(text: Optional[str]) -> str:
    """Normalise whitespace, strip fences/HTML and stabilise table rows.

    Returns an empty string for ``None``/blank input so callers can branch on a
    single, predictable sentinel.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", str(text))
    text = text.replace("\u00a0", " ").replace("\r\n", "\n").replace("\r", "\n")
    text = _FENCE_RE.sub("", text)
    text = _HTML_TAG_RE.sub(" ", text)
    # Collapse runs of spaces but keep newline structure (tables/headings).
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def truncate_markdown(text: str, max_chars: int = 300_000) -> tuple[str, bool]:
    """Trim to ``max_chars`` on a line boundary; returns ``(text, was_truncated)``."""
    if len(text) <= max_chars:
        return text, False
    cut = text.rfind("\n", 0, max_chars)
    if cut < max_chars // 2:  # single giant line: hard cut instead
        cut = max_chars
    return text[:cut].rstrip(), True


def first_heading(text: str) -> Optional[str]:
    """Return the first markdown heading (H1-H6) or ``None``."""
    match = _HEADING_RE.search(text)
    return match.group(1).strip() if match else None


# --------------------------------------------------------------------------- #
# Tables
# --------------------------------------------------------------------------- #
@dataclass
class MarkdownTable:
    """A parsed pipe table: ``headers`` plus raw ``rows`` of cells."""

    headers: list[str]
    rows: list[list[str]] = field(default_factory=list)
    start_line: int = 0

    @property
    def normalized_headers(self) -> list[str]:
        return [h.strip().lower().replace("\n", " ") for h in self.headers]


def _split_row(line: str) -> list[str]:
    inner = line.strip().strip("|")
    # Split on pipes that are not escaped.
    cells = re.split(r"(?<!\\)\|", inner)
    return [c.strip().replace("\\|", "|") for c in cells]


def _is_separator_row(cells: list[str]) -> bool:
    if not cells:
        return False
    return all(re.fullmatch(r":?-{2,}:?", c.replace(" ", "")) or c == "" for c in cells) and any(
        "-" in c for c in cells
    )


def iter_markdown_tables(text: str) -> Iterator[MarkdownTable]:
    """Yield every GitHub-style pipe table found in ``text``."""
    lines = text.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        if not _TABLE_ROW_RE.match(line):
            i += 1
            continue
        start = i
        headers = _split_row(line)
        i += 1
        if i >= len(lines) or not _is_separator_row(_split_row(lines[i])):
            continue  # header must be followed by |---|---|
        i += 1
        rows: list[list[str]] = []
        while i < len(lines) and _TABLE_ROW_RE.match(lines[i]):
            cells = _split_row(lines[i])
            if not _is_separator_row(cells):
                rows.append(cells)
            i += 1
        yield MarkdownTable(headers=headers, rows=rows, start_line=start)


def table_to_records(table: MarkdownTable) -> list[dict[str, str]]:
    """Zip a table's rows against its headers (missing cells become ``""``)."""
    headers = [h or f"col_{idx}" for idx, h in enumerate(table.headers)]
    records: list[dict[str, str]] = []
    for row in table.rows:
        row = list(row) + [""] * (len(headers) - len(row))
        records.append(dict(zip(headers, row[: len(headers)])))
    return records


# --------------------------------------------------------------------------- #
# Layout detection
# --------------------------------------------------------------------------- #
def detect_layout(text: str) -> str:
    """Coarse classification used to pick prompts / fallbacks.

    Returns one of ``"empty"``, ``"tables"``, ``"headings_lists"``, ``"prose"``.
    """
    if not text or not text.strip():
        return "empty"
    table_lines = sum(1 for line in text.split("\n") if _TABLE_ROW_RE.match(line))
    heading_lines = len(_HEADING_RE.findall(text))
    bullet_lines = sum(1 for line in text.split("\n") if _BULLET_RE.match(line))
    if table_lines >= 4:
        return "tables"
    if heading_lines >= 2 or bullet_lines >= 3:
        return "headings_lists"
    return "prose"


# --------------------------------------------------------------------------- #
# Model-output repair
# --------------------------------------------------------------------------- #
def extract_json_block(text: str) -> Optional[str]:
    """Return the first balanced ``{...}`` object (or ``[...]``) in ``text``.

    Handles model chit-chat, Markdown fences and trailing commentary.
    """
    if not text:
        return None
    cleaned = _FENCE_RE.sub("", text).strip()
    start = None
    opener = closer = ""
    for idx, char in enumerate(cleaned):
        if char in "{[":
            start, opener = idx, char
            closer = "}" if char == "{" else "]"
            break
    if start is None:
        return None
    depth = 0
    in_string = False
    escaped = False
    for idx in range(start, len(cleaned)):
        char = cleaned[idx]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return cleaned[start : idx + 1]
    return None if depth else cleaned[start:]


def sanitize_model_text(text: Optional[str]) -> str:
    """Best-effort conversion of raw model output into a JSON string."""
    if not text:
        return ""
    block = extract_json_block(text)
    return block if block is not None else _FENCE_RE.sub("", text).strip()


def loads_lenient(text: str) -> Optional[Any]:
    """``json.loads`` that tolerates fences, trailing commas and commentary."""
    if not text:
        return None
    candidate = sanitize_model_text(text)
    if not candidate:
        return None
    for payload in (candidate, re.sub(r",\s*([}\]])", r"\1", candidate)):
        try:
            return json.loads(payload)
        except (json.JSONDecodeError, ValueError):
            continue
    return None


# --------------------------------------------------------------------------- #
# Value parsing
# --------------------------------------------------------------------------- #
def parse_number(text: Any) -> Optional[float]:
    """First number in ``text`` (handles ``1,299``, ``12.5M``, ``45%``)."""
    if text is None or isinstance(text, bool):
        return None
    if isinstance(text, (int, float)):
        return float(text)
    match = _NUMBER_RE.search(str(text).replace("\u00a0", " "))
    if not match:
        return None
    try:
        return float(match.group(0).replace(",", "").replace("_", ""))
    except ValueError:
        return None


_MONEY_TOKEN_RE = re.compile(
    r"(?P<currency>[$€£¥₹]|USD|EUR|GBP|JPY|INR|CAD|AUD|CHF)?\s*"
    r"(?P<amount>-?\d[\d,_]*(?:\.\d+)?)\s*"
    r"(?P<suffix>[kKmMbB])?",
    re.VERBOSE,
)
_SUFFIX_MULTIPLIER = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}
_SYMBOL_TO_CODE = {"$": "USD", "€": "EUR", "£": "GBP", "¥": "JPY", "₹": "INR"}


def parse_money(text: Any) -> Optional[dict[str, Any]]:
    """Extract ``{"amount": float, "currency": str|None, "display": str}``."""
    if text is None:
        return None
    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return {"amount": float(text), "currency": None, "display": str(text)}
    raw = str(text).strip()
    if not raw:
        return None
    match = _MONEY_TOKEN_RE.search(raw)
    if not match:
        return None
    try:
        amount = float(match.group("amount").replace(",", "").replace("_", ""))
    except ValueError:
        return None
    suffix = match.group("suffix")
    if suffix:
        amount *= _SUFFIX_MULTIPLIER[suffix.lower()]
    currency = match.group("currency")
    if currency:
        currency = _SYMBOL_TO_CODE.get(currency, currency.upper())
    return {"amount": amount, "currency": currency, "display": raw}


def parse_bool_token(text: Any) -> Optional[bool]:
    """Interpret feature-matrix cells: ``yes``/``✓``/``no``/``—``/``n/a``."""
    if isinstance(text, bool):
        return text
    if text is None:
        return None
    token = str(text).strip().lower()
    if not token or token in {"-", "—", "–", "?", "n/a", "na", "tbd", "..."}:
        return None
    positives = {"yes", "y", "✓", "✔", "x", "true", "supported", "full", "included"}
    negatives = {"no", "n", "✗", "✘", "false", "not supported", "excluded", "-"}
    if token in positives:
        return True
    if token in negatives:
        return False
    if "not supported" in token or token.startswith("un"):
        return False
    return None


_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")
_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "of", "to", "in", "on", "for", "with",
    "is", "are", "was", "were", "it", "this", "that", "as", "at", "by", "from",
    "be", "has", "have", "will", "can", "not", "its", "their", "they",
}


def split_sentences(text: str) -> list[str]:
    """Naive sentence splitter - good enough for scoring and summaries."""
    if not text:
        return []
    parts = [p.strip() for p in _SENTENCE_SPLIT_RE.split(text)]
    return [p for p in parts if len(p) > 2]


# --------------------------------------------------------------------------- #
# Lexicon sentiment (fallback only)
# --------------------------------------------------------------------------- #
_POSITIVE_WORDS = {
    "good", "great", "excellent", "best", "love", "loved", "fast", "powerful",
    "affordable", "cheap", "cheaper", "easy", "reliable", "stable", "win",
    "winner", "recommend", "recommended", "impressive", "smooth", "intuitive",
    "generous", "free", "unlimited", "boost", "growth", "surge", "record",
    "profit", "partnership", "innovation", "leading", "strong", "up", "gain",
}
_NEGATIVE_WORDS = {
    "bad", "worst", "hate", "slow", "expensive", "pricey", "buggy", "broken",
    "outage", "down", "fail", "failed", "failure", "loss", "drop", "fell",
    "plunge", "layoff", "lawsuit", "recall", "security", "breach", "risk",
    "poor", "confusing", "limited", "unreliable", "downtime", "overpriced",
    "criticism", "concern", "delay", "cancel", "penalty", "fine",
}


def score_sentiment_text(text: str) -> dict[str, Any]:
    """Lexicon-based sentiment in ``[-1, 1]`` plus the evidence counts.

    Intentionally simple: this path only runs when the LLM is unavailable, and
    its job is to produce a *defensible* number with low confidence, not a
    polished one.
    """
    words = re.findall(r"[a-z']+", (text or "").lower())
    positive = sum(1 for w in words if w in _POSITIVE_WORDS)
    negative = sum(1 for w in words if w in _NEGATIVE_WORDS)
    total = positive + negative
    score = 0.0 if total == 0 else round((positive - negative) / total, 4)
    coverage = min(1.0, total / max(1, len(words) / 20))
    return {
        "score": score,
        "positive": positive,
        "negative": negative,
        "sample_size": len(words),
        "confidence": round(0.5 * coverage, 4),
    }


# --------------------------------------------------------------------------- #
# Fallback extractors -> schema-shaped dicts (still Pydantic-validated)
# --------------------------------------------------------------------------- #
def _guess_vendor(text: str, headings: list[str]) -> Optional[str]:
    for heading in headings:
        lowered = heading.lower()
        if any(word in lowered for word in ("pricing", "plans", "price")):
            cleaned = re.sub(
                r"\b(pricing|plans?|price|and|for|of|the)\b", " ", heading, flags=re.I
            )
            cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -–—|")
            if cleaned:
                return cleaned
    return headings[0] if headings else None


def _guess_currency(text: str) -> Optional[str]:
    if "$" in text or re.search(r"\bUSD\b", text):
        return "USD"
    if "€" in text or re.search(r"\bEUR\b", text):
        return "EUR"
    if "£" in text or re.search(r"\bGBP\b", text):
        return "GBP"
    if "₹" in text:
        return "INR"
    if "¥" in text:
        return "JPY"
    return None


def fallback_pricing_matrix(markdown: str, source_url: Optional[str] = None) -> dict:
    """Build a :class:`PricingMatrix` payload from tables / plan headings."""
    warnings: list[str] = []
    missing: list[str] = []
    plans: list[dict] = []
    usage_rates: list[dict] = []
    free_tier: dict | None = None

    tables = list(iter_markdown_tables(markdown))
    plan_words = re.compile(r"plan|tier|price|pricing|month|year|seat|seat|free|pro|basic|enterprise|starter|team|business", re.I)

    for table in tables:
        headers = table.normalized_headers
        header_blob = " ".join(headers)
        records = table_to_records(table)
        if plan_words.search(header_blob):
            for record in records:
                name = next(
                    (v for k, v in record.items() if v and re.search(r"plan|tier|name|plan name|package", k, re.I)),
                    None,
                ) or next((v for v in record.values() if v), "")
                if not name:
                    continue
                price_cell = next(
                    (v for k, v in record.items() if v and re.search(r"price|cost|\$", k + " " + v, re.I)),
                    None,
                )
                money = parse_money(price_cell)
                period_cell = next(
                    (v for k, v in record.items() if re.search(r"period|billing|cycle|interval", k, re.I)),
                    price_cell or "",
                )
                seat_key = next(
                    (h for h in headers if re.search(r"seat|user|member", h, re.I)), None
                )
                seats_number = parse_number(record.get(seat_key, "")) if seat_key else None
                plans.append(
                    {
                        "name": name.strip(),
                        "price": money["amount"] if money else None,
                        "price_display": money["display"] if money else price_cell or None,
                        "currency": (money or {}).get("currency"),
                        "billing_period": str(period_cell or ""),
                        "seats": int(seats_number) if seats_number is not None else None,
                        "included_features": [
                            v.strip()
                            for v in record.values()
                            if v and v.strip() and v.strip() != name.strip()
                        ][:6],
                    }
                )
        elif re.search(
            r"token|request|gb|mb|overage|metered|usage|rate|metric|unit|per\b",
            header_blob,
            re.I,
        ):
            for record in records:
                metric = next(
                    (v for k, v in record.items() if re.search(r"metric|unit|usage|what", k, re.I) and v),
                    None,
                ) or next((v for v in record.values() if v), "")
                price_cell = next(
                    (v for k, v in record.items() if re.search(r"price|rate|cost", k, re.I) and v),
                    None,
                )
                money = parse_money(price_cell)
                if not metric:
                    continue
                usage_rates.append(
                    {
                        "metric": metric.strip(),
                        "price": money["amount"] if money else None,
                        "price_display": money["display"] if money else None,
                        "currency": (money or {}).get("currency"),
                        "unit": str(
                            next(
                                (v for k, v in record.items() if re.search(r"unit|per", k, re.I) and v),
                                "",
                            )
                        ),
                    }
                )

    # Plan-style headings with bullet/price lines instead of a table.
    if not plans:
        current: dict | None = None
        for line in markdown.split("\n"):
            heading = _HEADING_RE.match(line)
            bullet = _BULLET_RE.match(line)
            if heading:
                title = heading.group(1).strip()
                if plan_words.search(title) and not re.fullmatch(
                    r"(pricing|price|plans?|faqs?)", title, re.I
                ):
                    current = {
                        "name": title,
                        "price": None,
                        "price_display": None,
                        "currency": None,
                        "billing_period": "",
                        "seats": None,
                        "included_features": [],
                    }
                    plans.append(current)
                    continue
                current = None
            if current is not None and bullet:
                body = bullet.group(1).strip()
                money = parse_money(body)
                if money and current["price"] is None and re.search(
                    r"\d", body
                ):
                    current["price"] = money["amount"]
                    current["price_display"] = money["display"]
                    current["currency"] = money["currency"]
                    if re.search(r"/\s*(mo|month)|per month|monthly", body, re.I):
                        current["billing_period"] = "monthly"
                    elif re.search(r"/\s*(yr|year)|per year|annual", body, re.I):
                        current["billing_period"] = "yearly"
                else:
                    current["included_features"].append(body)
            elif current is not None and not heading and not bullet:
                stripped = line.strip()
                if stripped and current["price"] is None:
                    money = parse_money(stripped)
                    if money and re.search(r"[$€£¥]|\d", stripped):
                        current["price"] = money["amount"]
                        current["price_display"] = money["display"]
                        current["currency"] = money["currency"]

    if re.search(r"\bfree\b|\btrial\b", markdown, re.I):
        snippet = re.search(
            r"([^\n]*(?:free|trial)[^\n]*)", markdown, re.I
        )
        free_tier = {
            "available": True,
            "description": snippet.group(1).strip() if snippet else None,
            "limits": [],
        }

    enterprise = re.search(r"([^\n]*enterprise[^\n]*(?:sales|custom|contact)[^\n]*)", markdown, re.I)

    if not plans and not usage_rates:
        missing.extend(["plans", "usage_based_rates"])
        warnings.append("fallback: no recognisable pricing table or plan headings found")

    headings = [h for h in (_HEADING_RE.match(line).group(1) for line in markdown.split("\n") if _HEADING_RE.match(line))]
    return {
        "vendor": _guess_vendor(markdown, headings),
        "source_url": source_url,
        "currency": _guess_currency(markdown),
        "plans": plans,
        "usage_based_rates": usage_rates,
        "free_tier": free_tier,
        "enterprise_note": enterprise.group(1).strip() if enterprise else None,
        "missing_fields": missing,
        "warnings": warnings or ["fallback: extracted by heuristic parser, not the LLM"],
    }


def fallback_feature_comparison(markdown: str, source_url: Optional[str] = None) -> dict:
    """Build a :class:`FeatureComparison` payload from tables and bullets."""
    warnings: list[str] = []
    missing: list[str] = []
    categories: list[dict] = []

    for table in iter_markdown_tables(markdown):
        headers = table.headers
        records = table_to_records(table)
        if len(headers) < 2 or not records:
            continue
        feature_key = headers[0]
        features: list[dict] = []
        for record in records:
            name = (record.get(feature_key) or "").strip()
            if not name:
                continue
            cells = [v for k, v in record.items() if k != feature_key]
            joined = " | ".join(c for c in cells if c)
            truth = parse_bool_token(joined.split("|")[0] if joined else "")
            if truth is True:
                support = "supported"
            elif truth is False:
                support = "not_supported"
            elif joined.strip() in {"-", "", "—"} or not joined.strip():
                support = "unknown"
            else:
                support = "partial" if re.search(r"limited|basic|partial|addon|paid", joined, re.I) else "unknown"
            features.append(
                {
                    "name": name,
                    "support": support,
                    "value": joined or None,
                    "notes": None,
                }
            )
        if features:
            categories.append(
                {
                    "name": first_heading(_slice_around(markdown, table.start_line)) or feature_key,
                    "features": features,
                }
            )

    # Bullet fallback when no tables exist.
    if not categories:
        current_name: Optional[str] = None
        collected: list[dict] = []
        for line in markdown.split("\n"):
            heading = _HEADING_RE.match(line)
            bullet = _BULLET_RE.match(line)
            if heading:
                if collected and current_name:
                    categories.append({"name": current_name, "features": collected})
                current_name = heading.group(1).strip()
                collected = []
            elif bullet:
                body = bullet.group(1).strip()
                if not body:
                    continue
                truth = parse_bool_token(body)
                if truth is None and ":" in body:
                    label, _, value = body.partition(":")
                    collected.append(
                        {"name": label.strip(), "support": "unknown", "value": value.strip() or None, "notes": None}
                    )
                else:
                    collected.append(
                        {
                            "name": body,
                            "support": "supported" if truth else ("not_supported" if truth is False else "unknown"),
                            "value": None,
                            "notes": None,
                        }
                    )
        if collected and current_name:
            categories.append({"name": current_name, "features": collected})

    if not categories:
        missing.append("categories")
        warnings.append("fallback: no comparison tables or feature lists recognised")

    headings = [h for h in (_HEADING_RE.match(line).group(1) for line in markdown.split("\n") if _HEADING_RE.match(line))]
    return {
        "subject": headings[0] if headings else None,
        "source_url": source_url,
        "categories": categories,
        "missing_fields": missing,
        "warnings": warnings or ["fallback: extracted by heuristic parser, not the LLM"],
    }


def _slice_around(text: str, line_no: int, radius: int = 6) -> str:
    lines = text.split("\n")
    start = max(0, line_no - radius)
    return "\n".join(lines[start:line_no])


def fallback_market_news(markdown: str, source_url: Optional[str] = None) -> dict:
    """Build a :class:`MarketNews` payload from links, headings and bullets."""
    warnings: list[str] = []
    items: list[dict] = []
    seen_titles: set[str] = set()

    def _push(title: str, url: Optional[str], summary: Optional[str], date_text: Optional[str]) -> None:
        title = title.strip()
        if not title or title.lower() in seen_titles:
            return
        seen_titles.add(title.lower())
        import datetime as _dt

        parsed = None
        if date_text:
            for fmt in ("%Y-%m-%d", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%m/%d/%Y"):
                try:
                    parsed = _dt.datetime.strptime(date_text.strip(), fmt).date()
                    break
                except ValueError:
                    continue
        if date_text and parsed is None:
            warnings.append(f"fallback: unparsed date '{date_text.strip()}' for '{title[:40]}'")
        items.append(
            {
                "title": title,
                "url": url,
                "source": None,
                "published_date": parsed,
                "published_date_raw": date_text.strip() if date_text else None,
                "summary": (summary or "").strip() or None,
                "entities": [],
                "sentiment_hint": None,
            }
        )

    # 1) Bullets / paragraphs that contain a markdown link.
    for line in markdown.split("\n"):
        match = _LINK_RE.search(line)
        bullet = _BULLET_RE.match(line)
        if match:
            title, url = match.group(1), match.group(2)
            if url.startswith("/"):
                base = re.match(r"(https?://[^/]+)", source_url or "")
                url = (base.group(1) + url) if base else url
            summary = _LINK_RE.sub("", line).strip(" -–—•*|")
            date_match = re.search(
                r"(\d{4}-\d{2}-\d{2}|\w{3,9} \d{1,2},? \d{4}|\d{1,2} \w{3,9} \d{4})", line
            )
            _push(title, url, summary or None, date_match.group(1) if date_match else None)
        elif bullet and re.search(r"\d{4}|\bannounc|launch|raises|acquir|funding|report", line, re.I):
            body = bullet.group(1).strip()
            date_match = re.search(
                r"(\d{4}-\d{2}-\d{2}|\w{3,9} \d{1,2},? \d{4}|\d{1,2} \w{3,9} \d{4})", body
            )
            url_match = _URL_RE.search(body)
            _push(
                body,
                url_match.group(0) if url_match else None,
                None,
                date_match.group(1) if date_match else None,
            )

    # 2) Headings under a "News" style section.
    news_heading = re.search(r"^\s{0,3}#{1,6}\s+(.*\b(news|announcements|press|updates)\b.*?)\s*$", markdown, re.I | re.M)
    if news_heading:
        section_start = markdown[: news_heading.start()].count("\n")
        section = "\n".join(markdown.split("\n")[section_start : section_start + 60])
        for heading in _HEADING_RE.finditer(section):
            title = heading.group(1).strip()
            if title.lower() == news_heading.group(1).strip().lower():
                continue
            _push(title, None, None, None)

    missing: list[str] = []
    if not items:
        missing.append("items")
        warnings.append("fallback: no links or dated headlines recognised as news items")
    return {
        "market_segment": None,
        "source_url": source_url,
        "items": items,
        "missing_fields": missing,
        "warnings": warnings or ["fallback: extracted by heuristic parser, not the LLM"],
    }


def fallback_sentiment_score(markdown: str, source_url: Optional[str] = None) -> dict:
    """Lexicon sentiment over the whole document plus per-section aspects."""
    overall = score_sentiment_text(markdown)
    score = overall["score"]

    aspects: list[dict] = []
    sections: list[tuple[str, str]] = []
    current_title: Optional[str] = None
    current_lines: list[str] = []
    for line in markdown.split("\n"):
        heading = _HEADING_RE.match(line)
        if heading:
            if current_title:
                sections.append((current_title, "\n".join(current_lines)))
            current_title, current_lines = heading.group(1).strip(), []
        else:
            current_lines.append(line)
    if current_title:
        sections.append((current_title, "\n".join(current_lines)))

    for title, body in sections:
        if not body.strip():
            continue
        section_score = score_sentiment_text(body)
        if section_score["positive"] + section_score["negative"] >= 2:
            aspects.append(
                {
                    "aspect": title,
                    "score": section_score["score"],
                    "rationale": f"lexicon counts: +{section_score['positive']}/-{section_score['negative']}",
                }
            )

    if score >= 0.15:
        label = "positive"
    elif score <= -0.15:
        label = "negative"
    elif aspects and min(a["score"] for a in aspects) < -0.1 and max(a["score"] for a in aspects) > 0.1:
        label = "mixed"
    else:
        label = "neutral"

    headings = [
        m.group(1).strip()
        for m in _HEADING_RE.finditer(markdown)
    ]
    warnings = ["fallback: lexicon sentiment, LLM path unavailable"]
    if overall["sample_size"] == 0:
        warnings.append("fallback: no analysable words found")
    return {
        "subject": headings[0] if headings else None,
        "source_url": source_url,
        "overall_score": score,
        "label": label,
        "confidence": overall["confidence"],
        "sample_size": overall["sample_size"],
        "aspects": aspects,
        "missing_fields": [] if headings else ["subject"],
        "warnings": warnings,
    }
