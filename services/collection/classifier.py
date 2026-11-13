"""Page classification using URL, title, metadata, headings and visible text."""

from __future__ import annotations

import re
from urllib.parse import urlsplit

from .models import PageCategory, PageClassification

_PATTERNS: dict[PageCategory, dict[str, tuple[str, ...]]] = {
    PageCategory.PRICING: {
        "url": (r"pricing|plans?|packages?|cost|subscribe|billing",),
        "title": (r"\bpricing\b|\bplans?\b|\bsubscriptions?\b",),
        "heading": (r"\bpricing\b|\bplans?\b|\bsubscriptions?\b|\bchoose a plan\b",),
        "text": (
            r"per\s+(?:month|user|seat)\b",
            r"/\s*(?:mo|month|yr|year)\b",
            r"billed\s+(?:monthly|annually|yearly)",
            r"\bfree\s+(?:plan|tier|trial)\b",
            r"\benterprise\b.{0,40}\bcontact\s+sales\b",
        ),
    },
    PageCategory.FEATURES: {
        "url": (r"features?|capabilities|solutions|use-cases|platform|integrations",),
        "title": (r"\bfeatures?\b|\bcapabilities\b|\bintegrations\b",),
        "heading": (r"\bfeatures?\b|\bcapabilities\b|\bwhat you can do\b",),
        "text": (
            r"\bfeatures?\b",
            r"\bintegrations?\b",
            r"\bavailable on\b.{0,40}\bplan\b",
        ),
    },
    PageCategory.CHANGELOG: {
        "url": (r"changelog|change-log|release-notes|releases?|whats-new|what-s-new|updates?",),
        "title": (r"changelog|\brelease notes\b|\bwhat'?s new\b",),
        "heading": (r"changelog|\brelease notes\b|\bwhat'?s new\b|\bversion\b",),
        "text": (
            r"\bchangelog\b",
            r"\brelease notes\b",
            r"\bversion\s+\d+(?:\.\d+)+",
            r"\bnow available\b",
            r"\bimproved\b.*\bfixed\b",
        ),
    },
    PageCategory.ANNOUNCEMENTS: {
        "url": (r"announcements?|press|newsroom|news|updates?",),
        "title": (r"announc|\bpress\b|\bnewsroom\b|\bnews\b|\blaunch",),
        "heading": (r"announc|\bpress\b|\bnewsroom\b|\bnews\b",),
        "text": (
            r"\bannounc(?:e|es|ed|ement)\b",
            r"\bpress release\b",
            r"\bwe(?:'re| are) (?:excited|thrilled|proud) to\b",
            r"\bnow available\b",
        ),
    },
    PageCategory.PRODUCT: {
        "url": (r"product|products|platform|solutions?|features?",),
        "title": (r"\bproduct\b|\bplatform\b|\bsolution\b",),
        "heading": (r"\bproduct\b|\bplatform\b|\bsolution\b",),
        "text": (r"\bproduct\b", r"\bplatform\b", r"\bworkflow\b"),
    },
    PageCategory.BLOG: {
        "url": (r"blog|articles?|insights?|resources?|guides?|learn",),
        "title": (r"\bblog\b|\barticles?\b|\binsights?\b|\bresources?\b",),
        "heading": (r"\bblog\b|\barticles?\b|\binsights?\b",),
        "text": (r"\bblog\b", r"\bread more\b"),
    },
    PageCategory.COMPANY: {
        "url": (r"about|company|team|careers|jobs|contact",),
        "title": (r"\babout\b|\bcompany\b|\bteam\b|\bcareers?\b",),
        "heading": (r"\babout\b|\bcompany\b|\bour team\b",),
        "text": (r"\babout us\b", r"\bour mission\b", r"\bfounded in\b"),
    },
}

_URL_WEIGHTS = {"url": 1.2, "title": 1.0, "heading": 0.7, "text": 0.25}


def _compile_scores(
    field_name: str,
    value: str,
    weight: float,
    scores: dict[PageCategory, float],
    signals: dict[PageCategory, list[str]],
    category: PageCategory,
    patterns: tuple[str, ...],
) -> None:
    if not value:
        return
    for pattern in patterns:
        match = re.search(pattern, value, re.IGNORECASE)
        if match:
            scores[category] += weight
            if len(signals[category]) < 6:
                signals[category].append(f"{field_name}:{match.group(0)[:60]}")


def classify_page(
    url: str,
    *,
    title: str = "",
    meta_description: str = "",
    headings: list[str] | None = None,
    text: str = "",
) -> PageClassification:
    """Multi-label classification. Unknown pages remain ``general``."""
    headings = headings or []
    try:
        path = urlsplit(url).path or "/"
    except ValueError:
        path = url
    haystacks = {
        "url": path,
        "title": title or "",
        "heading": " | ".join(headings[:20]),
        "text": (text or "")[:12_000],
    }
    scores: dict[PageCategory, float] = {category: 0.0 for category in PageCategory}
    signals: dict[PageCategory, list[str]] = {category: [] for category in PageCategory}

    for category, fields in _PATTERNS.items():
        for field_name, patterns in fields.items():
            _compile_scores(
                field_name,
                haystacks[field_name],
                _URL_WEIGHTS[field_name],
                scores,
                signals,
                category,
                patterns,
            )

    # Special combined evidence: dated update lists are usually changelogs.
    if re.search(r"\b(?:version|v)\s*\d+(?:\.\d+)+", haystacks["text"], re.IGNORECASE) and re.search(
        r"\b(?:new|improved|fixed|added|changed)\b", haystacks["text"], re.IGNORECASE
    ):
        scores[PageCategory.CHANGELOG] += 1.0
        signals[PageCategory.CHANGELOG].append("text:version+change-verbs")

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    selected = [category for category, score in ranked if score >= 1.0]
    if not selected:
        selected = [PageCategory.GENERAL]
    primary = selected[0]
    # A pricing page that also mentions features remains primarily pricing.
    total = sum(scores[c] for c in selected) or 1.0
    confidence = min(1.0, max(0.2, scores[primary] / total + min(0.4, scores[primary] / 6)))
    return PageClassification(
        primary=primary,
        categories=selected,
        confidence=confidence,
        signals=signals.get(primary, []),
    )
