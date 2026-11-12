"""Deterministic extractors for pricing, features, announcements and fallback.

The extractors never invent values. Missing information is represented by
``None``/``[]`` plus ``missing_fields`` exactly like the existing Gemini/Pydantic
contracts, so downstream validation accepts the payload without changes.
"""

from __future__ import annotations

import re
from typing import Any, Iterable, Optional
from urllib.parse import urljoin

from .cleaning import (
    extract_meta_description,
    find_date,
    first_paragraphs,
    normalize_billing_period,
    normalize_currency,
    parse_price,
)
from .models import (
    Evidence,
    ExtractedAnnouncement,
    ExtractedFeature,
    ExtractedPlan,
    PageCategory,
    PageClassification,
    PageSnapshot,
)

_PLAN_HEADER_RE = re.compile(r"plan|tier|package|edition|product|name", re.IGNORECASE)
_PRICE_HEADER_RE = re.compile(r"price|cost|amount|rate", re.IGNORECASE)
_MONTHLY_HEADER_RE = re.compile(r"monthly|per\s*month|/\s*mo\b|mo\b", re.IGNORECASE)
_ANNUAL_HEADER_RE = re.compile(r"annual|yearly|per\s*year|/\s*yr\b|year\b", re.IGNORECASE)
_BILLING_HEADER_RE = re.compile(r"billing|period|cycle|interval", re.IGNORECASE)
_SEATS_HEADER_RE = re.compile(r"seat|user|member|license", re.IGNORECASE)
_METRIC_HEADER_RE = re.compile(r"metric|usage|unit|what|feature", re.IGNORECASE)
_UNIT_HEADER_RE = re.compile(r"unit|per\b", re.IGNORECASE)

_POSITIVE_CELLS = {
    "yes", "y", "✓", "✔", "true", "included", "supported", "full", "available",
    "x", "✅",
}
_NEGATIVE_CELLS = {
    "no", "n", "✗", "✘", "false", "not included", "not supported", "unavailable",
    "excluded", "—", "-", "–",
}
_PARTIAL_RE = re.compile(r"limited|basic|partial|add-?on|paid only|some plans", re.IGNORECASE)
_NAV_LINE_RE = re.compile(
    r"^(?:home|pricing|features?|product|solutions?|docs?|blog|about|contact|"
    r"login|sign\s*in|sign\s*up|get started|book a demo|careers|support|"
    r"privacy|terms|company|resources?|menu|search|close)$",
    re.IGNORECASE,
)
_RELEASE_VERB_RE = re.compile(
    r"\b(?:launch(?:ed|es)?|introduc(?:ed|ing)|releas(?:ed|ing)|announc(?:ed|ing)|"
    r"now available|added|improved|fixed|deprecated|updated|new feature)\b",
    re.IGNORECASE,
)
_DATE_LINE_RE = re.compile(
    r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b"
    r"|\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b"
    r"|\b\d{4}-\d{2}-\d{2}\b",
    re.IGNORECASE,
)

_BILLING_ENUM = {
    "hourly", "daily", "monthly", "yearly", "one_time", "per_token",
    "per_request", "usage", "other",
}


def _normalize_headers(table: dict[str, Any]) -> list[str]:
    return [str(header or "").strip().lower() for header in table.get("headers") or []]


def _column(headers: list[str], pattern: re.Pattern[str], *, exclude: Iterable[int] = ()) -> Optional[int]:
    excluded = set(exclude)
    for index, header in enumerate(headers):
        if index not in excluded and pattern.search(header):
            return index
    return None


def _cell(row: list[str], index: Optional[int]) -> str:
    if index is None or index >= len(row):
        return ""
    return str(row[index] or "").strip()


def _row_text(row: list[str]) -> str:
    return " | ".join(cell for cell in row if cell)


def _is_pricing_table(headers: list[str]) -> bool:
    blob = " ".join(headers)
    return bool(_PRICE_HEADER_RE.search(blob)) and bool(
        _PLAN_HEADER_RE.search(blob) or _MONTHLY_HEADER_RE.search(blob) or _ANNUAL_HEADER_RE.search(blob)
    )


def _is_feature_table(headers: list[str]) -> bool:
    if len(headers) < 2:
        return False
    if _is_pricing_table(headers):
        return False
    return not _METRIC_HEADER_RE.search(" ".join(headers))


def _meaningful_plan_name(name: str) -> bool:
    candidate = (name or "").strip()
    if not candidate or len(candidate) > 120:
        return False
    if _NAV_LINE_RE.match(candidate):
        return False
    if re.fullmatch(r"[\d\W]+", candidate):
        return False
    return True


def _period_from_header(header: str, display: str, billing_state: str) -> str:
    if _ANNUAL_HEADER_RE.search(header):
        if re.search(r"/\s*mo\b|per\s+month|monthly", display, re.IGNORECASE):
            return "yearly"  # monthly-equivalent price billed annually
        return "yearly"
    if _MONTHLY_HEADER_RE.search(header):
        return "monthly"
    return normalize_billing_period(f"{header} {display}", billing_state=billing_state)


def _plan_key(plan: ExtractedPlan) -> tuple[str, str, str]:
    return (
        plan.name.strip().lower(),
        plan.billing_period,
        (plan.price_display or "").strip().lower(),
    )


def _merge_plan(plans: dict[tuple[str, str, str], ExtractedPlan], plan: ExtractedPlan) -> None:
    key = _plan_key(plan)
    existing = plans.get(key)
    if existing is None:
        plans[key] = plan
        return
    for feature in plan.included_features:
        if feature not in existing.included_features:
            existing.included_features.append(feature)
    for evidence in plan.evidence:
        if evidence.snippet not in {e.snippet for e in existing.evidence}:
            existing.evidence.append(evidence)


def _extract_pricing_tables(
    snapshot: PageSnapshot,
    plans: dict[tuple[str, str, str], ExtractedPlan],
    usage_rates: list[dict[str, Any]],
    warnings: list[str],
) -> None:
    for table in snapshot.tables:
        headers = _normalize_headers(table)
        if not headers:
            continue
        if _is_pricing_table(headers):
            plan_col = _column(headers, _PLAN_HEADER_RE)
            monthly_col = _column(headers, _MONTHLY_HEADER_RE, exclude=[plan_col] if plan_col is not None else [])
            annual_col = _column(headers, _ANNUAL_HEADER_RE, exclude=[plan_col] if plan_col is not None else [])
            price_col = _column(headers, _PRICE_HEADER_RE, exclude={c for c in (plan_col, monthly_col, annual_col) if c is not None})
            billing_col = _column(headers, _BILLING_HEADER_RE)
            seats_col = _column(headers, _SEATS_HEADER_RE)
            feature_columns = [
                index for index, header in enumerate(headers)
                if index not in {plan_col, monthly_col, annual_col, price_col, billing_col, seats_col}
                and header
            ]
            for raw_row in table.get("rows") or []:
                row = [str(cell or "") for cell in raw_row]
                name = _cell(row, plan_col) or next((cell for cell in row if cell), "")
                if not _meaningful_plan_name(name):
                    continue
                snippet = _row_text(row)[:1000]
                included = []
                for index in feature_columns:
                    value = _cell(row, index)
                    if not value or value.lower() in _POSITIVE_CELLS | _NEGATIVE_CELLS:
                        continue
                    if re.fullmatch(r"[$€£¥₹]?\s*\d[\d,.]*", value):
                        continue
                    included.append(value[:300])
                seats = None
                seats_text = _cell(row, seats_col)
                seats_match = re.search(r"\d+", seats_text)
                if seats_match:
                    seats = int(seats_match.group(0))

                price_columns: list[tuple[Optional[int], str]] = []
                if monthly_col is not None:
                    price_columns.append((monthly_col, "monthly"))
                if annual_col is not None:
                    price_columns.append((annual_col, "yearly"))
                if not price_columns and price_col is not None:
                    price_columns.append((price_col, ""))

                if not price_columns:
                    # No recognizable price column: keep the plan if it clearly says contact sales.
                    contact = re.search(r"contact\s+sales|custom|quote|call us", snippet, re.IGNORECASE)
                    if contact:
                        _merge_plan(
                            plans,
                            ExtractedPlan(
                                name=name,
                                billing_period="other",
                                notes="contact sales / custom pricing",
                                included_features=included,
                                evidence=[Evidence(snapshot.final_url or snapshot.url, snippet, "table")],
                            ),
                        )
                    continue

                for column_index, header_period in price_columns:
                    display = _cell(row, column_index)
                    if not display:
                        continue
                    money = parse_price(display)
                    if money is None and re.search(r"contact\s+sales|custom|quote|call us", display, re.IGNORECASE):
                        _merge_plan(
                            plans,
                            ExtractedPlan(
                                name=name,
                                billing_period="other",
                                notes=display,
                                seats=seats,
                                included_features=included,
                                evidence=[Evidence(snapshot.final_url or snapshot.url, snippet, "table")],
                            ),
                        )
                        continue
                    if money is None:
                        continue
                    period = header_period or _period_from_header(
                        _cell(row, column_index), display, snapshot.billing_state
                    )
                    if period not in _BILLING_ENUM:
                        period = "other"
                    notes = None
                    if period == "yearly" and re.search(r"/\s*mo\b|per\s+month", display, re.IGNORECASE):
                        notes = "annual billing; displayed price is the monthly equivalent"
                    elif _cell(row, billing_col):
                        notes = _cell(row, billing_col)[:300]
                    _merge_plan(
                        plans,
                        ExtractedPlan(
                            name=name,
                            price=money["amount"],
                            price_display=display,
                            currency=money["currency"] or normalize_currency(_cell(row, column_index)),
                            billing_period=period,
                            seats=seats,
                            included_features=list(included),
                            notes=notes,
                            evidence=[Evidence(snapshot.final_url or snapshot.url, snippet, "table")],
                        ),
                    )

        elif re.search(r"metric|usage|token|request|overage|metered|rate", " ".join(headers), re.IGNORECASE):
            metric_col = _column(headers, _METRIC_HEADER_RE)
            price_col = _column(
                headers,
                re.compile(r"price|rate|cost", re.IGNORECASE),
                exclude=[metric_col] if metric_col is not None else (),
            )
            unit_col = _column(headers, _UNIT_HEADER_RE, exclude={c for c in (metric_col, price_col) if c is not None})
            for raw_row in table.get("rows") or []:
                row = [str(cell or "") for cell in raw_row]
                metric = _cell(row, metric_col) or next((cell for cell in row if cell), "")
                price_text = _cell(row, price_col)
                money = parse_price(price_text)
                if not metric or money is None:
                    continue
                if metric.lower() in {"plan", "price", "feature"}:
                    continue
                usage_rates.append(
                    {
                        "metric": metric[:200],
                        "price": money["amount"],
                        "price_display": price_text,
                        "currency": money["currency"],
                        "unit": _cell(row, unit_col)[:120],
                        "billing_period": "usage",
                        "included_quantity": None,
                        "evidence": [
                            Evidence(snapshot.final_url or snapshot.url, _row_text(row)[:1000], "table").to_dict()
                        ],
                    }
                )


_PRICE_ANY_RE = re.compile(
    r"(?P<display>(?:[$€£¥₹]\s?\d[\d,]*(?:\.\d+)?|[A-Z]{3}\s?\d[\d,]*(?:\.\d+)?)"
    r"\s*(?:/\s*(?:mo(?:nth)?|yr|year|user|seat)|per\s+(?:month|year|user|seat))?)",
    re.IGNORECASE,
)


def _extract_pricing_text(
    snapshot: PageSnapshot,
    plans: dict[tuple[str, str, str], ExtractedPlan],
    warnings: list[str],
) -> None:
    lines = [line.strip() for line in (snapshot.text or "").split("\n") if line.strip()]
    for index, line in enumerate(lines):
        match = _PRICE_ANY_RE.search(line)
        if not match:
            continue
        display = match.group("display").strip()
        money = parse_price(display)
        if money is None:
            continue
        # Candidate name: the same line before the price, otherwise the previous line.
        name = line[: match.start()].strip(" -–—:|")
        if len(name) < 2 or re.search(r"[$€£¥₹]", name):
            name = lines[index - 1] if index > 0 else ""
        if not _meaningful_plan_name(name) or len(name) > 60:
            continue
        if re.search(r"token|request|gb|mb|overage|usage", line, re.IGNORECASE):
            continue
        period = normalize_billing_period(line, billing_state=snapshot.billing_state)
        if period not in _BILLING_ENUM:
            period = "other"
        _merge_plan(
            plans,
            ExtractedPlan(
                name=name,
                price=money["amount"],
                price_display=display,
                currency=money["currency"],
                billing_period=period,
                evidence=[Evidence(snapshot.final_url or snapshot.url, line[:500], "text")],
            ),
        )


def extract_pricing(
    snapshots: Iterable[PageSnapshot],
    *,
    vendor: str = "",
) -> dict[str, Any]:
    plan_map: dict[tuple[str, str, str], ExtractedPlan] = {}
    usage_rates: list[dict[str, Any]] = []
    warnings: list[str] = []
    free_tier: Optional[dict[str, Any]] = None
    enterprise_note: Optional[str] = None
    source_url = ""
    currency: Optional[str] = None

    for snapshot in snapshots:
        if snapshot.status != "success":
            continue
        source_url = source_url or snapshot.final_url or snapshot.url
        _extract_pricing_tables(snapshot, plan_map, usage_rates, warnings)
        _extract_pricing_text(snapshot, plan_map, warnings)
        text = snapshot.text or ""
        if free_tier is None:
            free_match = re.search(
                r"([^\n]*(?:free\s+(?:plan|tier|trial|forever)|start\s+for\s+free)[^\n]*)",
                text,
                re.IGNORECASE,
            )
            if free_match:
                free_tier = {
                    "available": True,
                    "description": free_match.group(1).strip()[:500],
                    "limits": [],
                }
        if enterprise_note is None:
            enterprise = re.search(
                r"([^\n]*enterprise[^\n]*(?:contact\s+sales|custom|quote)[^\n]*)",
                text,
                re.IGNORECASE,
            )
            if enterprise:
                enterprise_note = enterprise.group(1).strip()[:500]

    plans = list(plan_map.values())
    for plan in plans:
        currency = currency or plan.currency

    missing: list[str] = []
    if not plans:
        missing.append("plans")
        warnings.append("no deterministic pricing plans detected")
    if not usage_rates:
        missing.append("usage_based_rates")

    return {
        "target": "pricing_matrix",
        "vendor": vendor or None,
        "source_url": source_url or None,
        "currency": currency,
        "plans": [plan.to_dict() for plan in plans],
        "usage_based_rates": usage_rates,
        "free_tier": free_tier,
        "enterprise_note": enterprise_note,
        "missing_fields": missing,
        "warnings": warnings,
        "source_snapshots": [
            {"url": s.final_url or s.url, "billing_state": s.billing_state}
            for s in snapshots
        ],
    }


def _support_of(cells: list[str]) -> tuple[str, list[str]]:
    joined = " ".join(cells).strip()
    lowered = joined.lower()
    supported_plans: list[str] = []
    if not joined:
        return "unknown", supported_plans
    if any(cell.lower() in _POSITIVE_CELLS for cell in cells if cell):
        return "supported", supported_plans
    if _PARTIAL_RE.search(lowered):
        return "partial", supported_plans
    if cells and all(
        (not cell) or cell.lower() in _NEGATIVE_CELLS for cell in cells
    ):
        return "not_supported", supported_plans
    return "unknown", supported_plans


def _extract_feature_tables(snapshot: PageSnapshot) -> list[ExtractedFeature]:
    features: list[ExtractedFeature] = []
    for table in snapshot.tables:
        headers = _normalize_headers(table)
        if not _is_feature_table(headers):
            continue
        plan_names = [str(header or "").strip() for header in table.get("headers") or [""]]
        for raw_row in table.get("rows") or []:
            row = [str(cell or "") for cell in raw_row]
            name = row[0].strip() if row else ""
            if not _meaningful_plan_name(name) or len(name) > 160:
                continue
            cells = row[1:]
            support, _ = _support_of(cells)
            supported_plans = [
                plan_names[index + 1]
                for index, cell in enumerate(cells)
                if index + 1 < len(plan_names)
                and cell.strip().lower() in _POSITIVE_CELLS
                and plan_names[index + 1]
            ]
            value = " | ".join(cell for cell in cells if cell)[:300] or None
            features.append(
                ExtractedFeature(
                    name=name,
                    category=(plan_names[0] if plan_names and plan_names[0] else "Features"),
                    support=support,
                    plans=supported_plans,
                    value=value,
                    evidence=[Evidence(snapshot.final_url or snapshot.url, _row_text(row)[:800], "table")],
                )
            )
    return features


def _extract_feature_lists(snapshot: PageSnapshot) -> list[ExtractedFeature]:
    features: list[ExtractedFeature] = []
    for group in snapshot.lists or []:
        heading = str(group.get("heading") or "").strip() or "Features"
        for item in group.get("items") or []:
            text = str(item or "").strip()
            if len(text) < 4 or len(text) > 240:
                continue
            if _NAV_LINE_RE.match(text):
                continue
            if re.search(r"\b(?:privacy|terms|cookie|©|all rights reserved)\b", text, re.IGNORECASE):
                continue
            name, _, value = text.partition(":")
            features.append(
                ExtractedFeature(
                    name=(name if value else text).strip()[:160],
                    category=heading[:120],
                    value=value.strip()[:300] or None,
                    support="unknown",
                    evidence=[Evidence(snapshot.final_url or snapshot.url, text[:500], "list")],
                )
            )
    return features


def extract_features(
    snapshots: Iterable[PageSnapshot],
    *,
    subject: str = "",
) -> dict[str, Any]:
    category_map: dict[str, list[ExtractedFeature]] = {}
    seen: set[str] = set()
    source_url = ""
    for snapshot in snapshots:
        if snapshot.status != "success":
            continue
        source_url = source_url or snapshot.final_url or snapshot.url
        for feature in _extract_feature_tables(snapshot) + _extract_feature_lists(snapshot):
            key = re.sub(r"\s+", " ", feature.name.lower())
            if key in seen:
                continue
            seen.add(key)
            category_map.setdefault(feature.category or "Features", []).append(feature)

    categories = [
        {"name": name, "features": [feature.to_dict() for feature in features]}
        for name, features in category_map.items()
    ]
    missing = [] if categories else ["categories"]
    return {
        "target": "feature_comparison",
        "subject": subject or None,
        "source_url": source_url or None,
        "categories": categories,
        "missing_fields": missing,
        "warnings": [] if categories else ["no deterministic feature rows detected"],
    }


def _announcement_candidates(snapshot: PageSnapshot) -> list[ExtractedAnnouncement]:
    items: list[ExtractedAnnouncement] = []
    lines = [line.strip() for line in (snapshot.text or "").split("\n") if line.strip()]

    for index, line in enumerate(lines):
        date_match = _DATE_LINE_RE.search(line)
        if not date_match:
            continue
        title = (line[: date_match.start()] + line[date_match.end() :]).strip(" -–—:|")
        if len(title) < 6:
            title = lines[index - 1] if index > 0 else ""
        if not title or _NAV_LINE_RE.match(title):
            continue
        summary = lines[index + 1] if index + 1 < len(lines) else ""
        if summary and _DATE_LINE_RE.search(summary):
            summary = ""
        date_iso, date_raw = find_date(date_match.group(0))
        items.append(
            ExtractedAnnouncement(
                title=title[:300],
                summary=summary[:1000],
                date=date_iso,
                date_raw=date_raw,
                url=snapshot.final_url or snapshot.url,
                evidence=[Evidence(snapshot.final_url or snapshot.url, line[:500], "text")],
            )
        )

    for group in snapshot.lists or []:
        heading = str(group.get("heading") or "").strip()
        for item in group.get("items") or []:
            text = str(item or "").strip()
            if len(text) < 10 or len(text) > 300:
                continue
            if not _RELEASE_VERB_RE.search(text):
                continue
            date_iso, date_raw = find_date(text)
            title = _DATE_LINE_RE.sub("", text).strip(" -–—:|")
            if not title:
                continue
            items.append(
                ExtractedAnnouncement(
                    title=title[:300],
                    summary="",
                    date=date_iso,
                    date_raw=date_raw,
                    url=snapshot.final_url or snapshot.url,
                    evidence=[Evidence(snapshot.final_url or snapshot.url, text[:500], "list")],
                )
            )
    return items


def extract_announcements(
    snapshots: Iterable[PageSnapshot],
    *,
    classification: Optional[PageClassification] = None,
    market_segment: str = "",
) -> dict[str, Any]:
    categories = set(classification.categories if classification else [])
    strong_category = bool(
        categories & {PageCategory.ANNOUNCEMENTS, PageCategory.CHANGELOG}
    )
    items: dict[str, ExtractedAnnouncement] = {}
    source_url = ""
    for snapshot in snapshots:
        if snapshot.status != "success":
            continue
        source_url = source_url or snapshot.final_url or snapshot.url
        text = snapshot.text or ""
        text_has_release_signal = bool(_RELEASE_VERB_RE.search(text)) and bool(_DATE_LINE_RE.search(text))
        if not strong_category and not text_has_release_signal:
            continue
        for item in _announcement_candidates(snapshot):
            if item.title.lower() in items:
                continue
            # Ordinary marketing blog posts are not product announcements.
            if not strong_category and not _RELEASE_VERB_RE.search(item.title + " " + item.summary):
                continue
            items[item.title.lower()] = item

    payload_items = []
    for item in list(items.values())[:40]:
        payload_items.append(
            {
                "title": item.title,
                "url": item.url,
                "source": None,
                "published_date": item.date,
                "published_date_raw": item.date_raw,
                "summary": item.summary or None,
                "entities": [],
                "sentiment_hint": None,
            }
        )
    return {
        "target": "market_news",
        "market_segment": market_segment or None,
        "source_url": source_url or None,
        "items": payload_items,
        "missing_fields": [] if payload_items else ["items"],
        "warnings": [] if payload_items else ["no dated announcements/changelog entries detected"],
    }


def extract_generic(
    snapshots: Iterable[PageSnapshot],
    *,
    classification: Optional[PageClassification] = None,
) -> dict[str, Any]:
    texts: list[str] = []
    headings: list[str] = []
    source_url = ""
    title = ""
    for snapshot in snapshots:
        if snapshot.status != "success":
            continue
        source_url = source_url or snapshot.final_url or snapshot.url
        title = title or snapshot.title
        texts.append(snapshot.text or "")
        headings.extend(snapshot.headings or [])
    combined = "\n\n".join(texts)
    summary = first_paragraphs(combined)
    product_details = []
    if title and summary:
        product_details.append(
            {"name": title[:200], "detail": summary, "source_url": source_url or None}
        )
    headings = list(dict.fromkeys(h.strip() for h in headings if h.strip()))[:40]
    return {
        "title": title or None,
        "source_url": source_url or None,
        "summary": summary or None,
        "headings": headings,
        "product_details": product_details,
        "classification": classification.to_dict() if classification else None,
        "text_length": len(combined),
    }


def to_schema_payload(payload: dict[str, Any], target: str) -> dict[str, Any]:
    """Strip evidence/metadata so the payload validates against Pydantic schemas."""
    if target == "pricing_matrix":
        return {
            "target": "pricing_matrix",
            "vendor": payload.get("vendor"),
            "source_url": payload.get("source_url"),
            "currency": payload.get("currency"),
            "plans": [
                {key: value for key, value in plan.items() if key not in {"evidence"}}
                for plan in payload.get("plans") or []
            ],
            "usage_based_rates": [
                {key: value for key, value in rate.items() if key not in {"evidence"}}
                for rate in payload.get("usage_based_rates") or []
            ],
            "free_tier": payload.get("free_tier"),
            "enterprise_note": payload.get("enterprise_note"),
            "missing_fields": list(payload.get("missing_fields") or []),
            "warnings": list(payload.get("warnings") or []),
        }
    if target == "feature_comparison":
        return {
            "target": "feature_comparison",
            "subject": payload.get("subject"),
            "source_url": payload.get("source_url"),
            "categories": [
                {
                    "name": category.get("name"),
                    "features": [
                        {
                            "name": feature.get("name"),
                            "support": feature.get("support") or "unknown",
                            "value": feature.get("value"),
                            "notes": feature.get("notes"),
                        }
                        for feature in category.get("features") or []
                    ],
                }
                for category in payload.get("categories") or []
            ],
            "missing_fields": list(payload.get("missing_fields") or []),
            "warnings": list(payload.get("warnings") or []),
        }
    if target == "market_news":
        return {
            "target": "market_news",
            "market_segment": payload.get("market_segment"),
            "source_url": payload.get("source_url"),
            "items": [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "source": item.get("source"),
                    "published_date": item.get("published_date"),
                    "published_date_raw": item.get("published_date_raw"),
                    "summary": item.get("summary"),
                    "entities": item.get("entities") or [],
                    "sentiment_hint": item.get("sentiment_hint"),
                }
                for item in payload.get("items") or []
            ],
            "missing_fields": list(payload.get("missing_fields") or []),
            "warnings": list(payload.get("warnings") or []),
        }
    return payload
