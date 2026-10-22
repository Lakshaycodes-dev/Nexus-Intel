"""Gemini 1.5 Flash integration: prompting, structured output, validation, fallbacks.

Pipeline (``GeminiService.extract``)::

    raw markdown
        -> normalise (utils.parser_helpers)
        -> [1] Gemini structured-output call (response_schema = Pydantic model)
              on ValidationError -> [2] repair call with the validation errors
              on failure          -> [3] heuristic fallback extractors
        -> Pydantic-validated result + warnings/missing_fields

Every layer returns a schema instance; only the *provenance* differs (``gemini``
vs ``fallback``), which is recorded in ``warnings`` so downstream consumers can
treat the two paths uniformly.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Optional

from pydantic import BaseModel, ValidationError

from schemas.pydantic_schemas import (
    TARGET_SCHEMAS,
    ExtractionModel,
    ExtractionTarget,
    FeatureComparison,
    MarketNews,
    PricingMatrix,
    SentimentScore,
)

from utils import parser_helpers as ph

logger = logging.getLogger(__name__)

__all__ = [
    "GeminiService",
    "ExtractionError",
    "build_prompt",
    "DEFAULT_MODEL",
]

DEFAULT_MODEL = "gemini-1.5-flash"

# Transient failures worth retrying: 429 rate limits, 5xx, network blips.
_RETRYABLE_STATUS = {429, 500, 502, 503, 504, 529}
_MAX_API_ATTEMPTS = 3
_BACKOFF_BASE_SECONDS = 2.0


class ExtractionError(RuntimeError):
    """Raised when *all* extraction paths (LLM + repair + fallback) failed."""

    def __init__(self, message: str, *, target: ExtractionTarget, errors: Optional[list[str]] = None):
        super().__init__(message)
        self.target = target
        self.errors = errors or []


# --------------------------------------------------------------------------- #
# Prompt engineering
# --------------------------------------------------------------------------- #
_SYSTEM_INSTRUCTION = """\
You are a precision data-extraction engine. You convert raw web markdown \
(scraped product, pricing, comparison and news pages) into JSON that matches a \
caller-supplied schema exactly.

Non-negotiable rules:
1. EXTRACT, NEVER INVENT. Every value you emit must be traceable to literal text \
in the source markdown. If a value is not stated, emit null (or [] for lists) and \
add its dotted path to "missing_fields".
2. PRESERVE EXACTNESS for names, labels and quoted strings - copy them character \
by character, including capitalisation. Numbers become bare JSON numbers with no \
currency symbols, units or separators ("$1,299/seat" -> price: 1299, \
price_display: "$1,299/seat").
3. NO INFERENCE across cells or sections: a blank, "—", "?" or "n/a" cell means \
unknown, not false.
4. OUTPUT CONTRACT: return a single JSON object only - no prose, no Markdown \
fences, no trailing commentary. The JSON must satisfy the schema completely, \
including the "target" discriminator field with its exact expected value.
5. Record every structural surprise (merged cells, missing columns, tables that \
are not tabular, dates you cannot parse) in "warnings" instead of guessing.
6. Do not copy instructions, prompt text or schema descriptions into the output. \
They are context, not data.
"""

_TARGET_BRIEFS: dict[ExtractionTarget, str] = {
    ExtractionTarget.PRICING_MATRIX: """\
Extract the PRICING MATRIX from the markdown:
- One entry in "plans" per published plan/SKU/column of the pricing table, in the
  order they appear. Price cell -> price (number), price_display (verbatim) and
  currency; the plan name is copied verbatim.
- Billing period comes from "/mo", "per month", "billed annually", etc.
- Metered rates (per 1M tokens, per request, overage) go to "usage_based_rates",
  never into "plans".
- "Contact sales" / "Custom" pricing means price: null plus a note in
  "enterprise_note". Free/trial offers populate "free_tier".
- Rows or columns that do not represent a real plan (footnotes, badges,
  "Most popular") are excluded.""",
    ExtractionTarget.FEATURE_COMPARISON: """\
Extract the FEATURE COMPARISON matrix from the markdown:
- Group features under their nearest heading as "categories".
- Each row becomes a "feature" with name copied verbatim and "support":
  supported (✓/Yes/Full), partial (limited/Basic/add-on), not_supported (✗/No),
  unknown (blank/—/?/n/a).
- Numeric limits ("10 GB", "Unlimited", "3 projects") go in "value" while support
  stays "unknown" unless the cell also carries an explicit yes/no signal.
- Keep footnote markers in "notes", not in "name".""",
    ExtractionTarget.MARKET_NEWS: """\
Extract MARKET NEWS items from the markdown:
- One "items" entry per article/announcement/headline, in document order.
- Copy the headline verbatim; put the link in "url" (absolute when a base URL is
  given), the byline/domain in "source", and parse the date into "published_date"
  (YYYY-MM-DD) while keeping the original text in "published_date_raw".
- "summary" is 1-2 sentences drawn only from the source text.
- "entities" lists companies/products/people named in the item.
- "sentiment_hint" is only set when the item itself states sentiment.""",
    ExtractionTarget.SENTIMENT_SCORE: """\
Extract a SENTIMENT SCORE from the markdown:
- "overall_score" spans -1 (uniformly negative) to 1 (uniformly positive); use 0
  when there is no sentiment evidence rather than guessing.
- "label" must be consistent with "overall_score" (>=0.15 positive, <=-0.15
  negative, otherwise neutral; "mixed" only when sections clearly disagree).
- "confidence" reflects evidence volume: sparse input -> low confidence.
- "aspects" covers each distinct sub-topic with real sentiment evidence
  (pricing, performance, support...), each scored -1..1 with a short rationale
  quoting or paraphrasing the source.
- "sample_size" is the number of statements the judgement is based on.""",
}


def build_prompt(
    target: ExtractionTarget,
    markdown: str,
    *,
    source_url: Optional[str] = None,
    layout: Optional[str] = None,
    validation_errors: Optional[list[str]] = None,
) -> str:
    """Assemble the user turn for one extraction call.

    ``validation_errors`` turns the prompt into a *repair* prompt: the model is
    shown exactly why its previous JSON was rejected and asked to fix it.
    """
    schema_cls = TARGET_SCHEMAS[target]
    parts: list[str] = []
    if validation_errors:
        parts.append(
            "Your previous response failed validation. Fix EVERY problem listed "
            "below and return the complete corrected JSON object only "
            "(no explanation, no fences):\n"
            + "\n".join(f"- {err}" for err in validation_errors)
        )
    parts.append(
        f"TASK: populate the {schema_cls.__name__} JSON schema.\n"
        f"Expected \"target\" value: \"{target.value}\"."
    )
    parts.append(_TARGET_BRIEFS[target])
    if source_url:
        parts.append(f"Source URL (use for absolute links): {source_url}")
    if layout:
        parts.append(
            f"Detected layout hint: {layout}. "
            "If this layout does not match the usual structure for this target, "
            "still extract what is unambiguous and record the surprise in "
            '"warnings".'
        )
    parts.append("SOURCE MARKDOWN:\n<markdown>\n" + markdown + "\n</markdown>")
    parts.append("Return the JSON object now.")
    return "\n\n".join(parts)


# --------------------------------------------------------------------------- #
# Service
# --------------------------------------------------------------------------- #
class GeminiService:
    """Thin, testable wrapper around the Google GenAI SDK.

    Parameters
    ----------
    api_key:
        Explicit key; falls back to ``GEMINI_API_KEY`` / ``GOOGLE_API_KEY``.
        The client is created lazily so the module can be imported (and the
        fallback path exercised) without any credentials.
    client:
        Dependency-injection hook: any object exposing
        ``models.generate_content(model=..., contents=..., config=...)``.
        Used by tests to run offline.
    """

    def __init__(
        self,
        *,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        client: Any = None,
        max_input_chars: int = 300_000,
        temperature: float = 0.0,
        max_output_tokens: int = 8192,
        max_repair_attempts: int = 1,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self._api_key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        self.model = model or os.getenv("GEMINI_MODEL") or DEFAULT_MODEL
        self._client = client
        self.max_input_chars = max_input_chars
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self.max_repair_attempts = max_repair_attempts
        self._sleep = sleep

    # -- client management -------------------------------------------------- #
    @property
    def client(self) -> Any:
        if self._client is None:
            if not self._api_key:
                raise ExtractionError(
                    "No Gemini credentials found. Set GEMINI_API_KEY (or pass "
                    "api_key=/client= to GeminiService) to enable the LLM path; "
                    "callers fall back to the heuristic extractor automatically.",
                    target=getattr(self, "_active_target", ExtractionTarget.PRICING_MATRIX),
                )
            from google import genai  # imported lazily: keeps offline use working

            self._client = genai.Client(api_key=self._api_key)
        return self._client

    def _generate(self, prompt: str) -> str:
        """One structured-output call with retry/backoff on transient errors."""
        from google.genai import errors as genai_errors
        from google.genai import types

        config = types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            response_mime_type="application/json",
            response_schema=self._active_schema,  # schema-constrained decoding
            temperature=self.temperature,
            max_output_tokens=self.max_output_tokens,
        )
        last_error: Optional[Exception] = None
        for attempt in range(1, _MAX_API_ATTEMPTS + 1):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                return self._response_text(response)
            except genai_errors.APIError as exc:  # type: ignore[misc]
                last_error = exc
                code = getattr(exc, "code", None)
                if code not in _RETRYABLE_STATUS:
                    raise ExtractionError(
                        f"Gemini API error {code}: {exc}",
                        target=self._active_target,
                    ) from exc
            except Exception as exc:  # httpx transport errors, timeouts, ...
                message = str(exc).lower()
                transient = any(
                    token in message
                    for token in ("timeout", "timed out", "unavailable", "connection", "503", "429")
                )
                if not transient:
                    raise ExtractionError(
                        f"Gemini call failed: {exc}", target=self._active_target
                    ) from exc
                last_error = exc
            if attempt < _MAX_API_ATTEMPTS:
                delay = _BACKOFF_BASE_SECONDS ** attempt
                logger.warning(
                    "Gemini call attempt %s/%s failed (%s); retrying in %.1fs",
                    attempt,
                    _MAX_API_ATTEMPTS,
                    last_error,
                    delay,
                )
                self._sleep(delay)
        raise ExtractionError(
            f"Gemini call failed after {_MAX_API_ATTEMPTS} attempts: {last_error}",
            target=self._active_target,
            errors=[str(last_error)] if last_error else [],
        )

    @staticmethod
    def _response_text(response: Any) -> str:
        """Prefer the SDK's parsed object; fall back to raw text."""
        parsed = getattr(response, "parsed", None)
        if isinstance(parsed, BaseModel):
            return parsed.model_dump_json()
        text = getattr(response, "text", None)
        if text:
            return text
        # Older/odd responses: dig into candidates manually.
        candidates = getattr(response, "candidates", None) or []
        for candidate in candidates:
            content = getattr(candidate, "content", None)
            parts = getattr(content, "parts", None) or []
            joined = "".join(getattr(p, "text", "") or "" for p in parts)
            if joined:
                return joined
        return ""

    # -- public API --------------------------------------------------------- #
    def extract(
        self,
        target: ExtractionTarget | str,
        markdown: Optional[str],
        *,
        source_url: Optional[str] = None,
    ) -> ExtractionModel:
        """Run the full pipeline and return a validated schema instance.

        Never raises for ordinary failures: LLM outage, missing credentials or
        unusable model output all degrade to the heuristic fallback (marked in
        ``warnings``). Only a fallback that also cannot produce a valid object
        - or an unknown target string - surfaces as :class:`ExtractionError`.
        """
        if isinstance(target, str):
            target = ExtractionTarget(target)  # raises ValueError for unknown targets
        self._active_target = target
        self._active_schema = TARGET_SCHEMAS[target]

        raw = ph.clean_markdown(markdown)
        raw, truncated = ph.truncate_markdown(raw, self.max_input_chars)
        if truncated:
            logger.warning("Input truncated to %s chars for %s", self.max_input_chars, target.value)

        if not raw:
            # Nothing to read: skip the API and return an honest, valid object.
            instance = self._build_fallback(target, "", source_url)
            instance.warnings.insert(0, "empty input markdown: nothing to extract")
            return instance

        layout = ph.detect_layout(raw)
        prompt = build_prompt(target, raw, source_url=source_url, layout=layout)
        validation_errors: list[str] = []

        try:
            for attempt in range(1 + self.max_repair_attempts):
                text = self._generate(prompt)
                instance = self._validate_text(target, text)
                if instance is not None:
                    if attempt:
                        instance.warnings.append(
                            "repaired: model output fixed after validation feedback"
                        )
                    if truncated:
                        instance.warnings.append("input truncated before extraction")
                    return instance
                validation_errors = self._last_errors
                logger.warning(
                    "%s attempt %s failed validation (%s)",
                    target.value,
                    attempt + 1,
                    "; ".join(validation_errors[:3]),
                )
                prompt = build_prompt(
                    target,
                    raw,
                    source_url=source_url,
                    layout=layout,
                    validation_errors=validation_errors,
                )
        except ExtractionError:
            # API outage / missing credentials / hard API error -> degrade.
            logger.exception("Gemini unavailable; using heuristic fallback for %s", target.value)
            return self._build_fallback(target, raw, source_url)

        # All LLM attempts produced invalid JSON -> heuristic fallback.
        logger.warning("LLM output unusable for %s; using heuristic fallback", target.value)
        return self._build_fallback(target, raw, source_url)

    # Convenience wrappers ------------------------------------------------- #
    def extract_pricing(self, markdown: Optional[str], *, source_url: Optional[str] = None) -> PricingMatrix:
        return self.extract(ExtractionTarget.PRICING_MATRIX, markdown, source_url=source_url)  # type: ignore[return-value]

    def extract_features(self, markdown: Optional[str], *, source_url: Optional[str] = None) -> FeatureComparison:
        return self.extract(ExtractionTarget.FEATURE_COMPARISON, markdown, source_url=source_url)  # type: ignore[return-value]

    def extract_news(self, markdown: Optional[str], *, source_url: Optional[str] = None) -> MarketNews:
        return self.extract(ExtractionTarget.MARKET_NEWS, markdown, source_url=source_url)  # type: ignore[return-value]

    def extract_sentiment(self, markdown: Optional[str], *, source_url: Optional[str] = None) -> SentimentScore:
        return self.extract(ExtractionTarget.SENTIMENT_SCORE, markdown, source_url=source_url)  # type: ignore[return-value]

    # -- internals ---------------------------------------------------------- #
    _active_target: ExtractionTarget = ExtractionTarget.PRICING_MATRIX
    _active_schema: type[ExtractionModel] = PricingMatrix
    _last_errors: list[str] = []

    def _validate_text(self, target: ExtractionTarget, text: Optional[str]) -> Optional[ExtractionModel]:
        """Parse + strictly validate model output; record errors for a repair."""
        schema_cls = TARGET_SCHEMAS[target]
        payload = ph.loads_lenient(text or "")
        if payload is None:
            self._last_errors = ["response was not parseable as JSON (see the output contract rule)"]
            return None
        if not isinstance(payload, dict):
            self._last_errors = [f"expected a JSON object, got {type(payload).__name__}"]
            return None
        try:
            return schema_cls.model_validate(payload)
        except ValidationError as exc:
            self._last_errors = [
                f"{'.'.join(str(p) for p in err['loc'])}: {err['msg']}"
                for err in exc.errors()[:12]
            ]
            return None

    def _build_fallback(
        self, target: ExtractionTarget, markdown: str, source_url: Optional[str]
    ) -> ExtractionModel:
        """Heuristic extraction; still fully Pydantic-validated."""
        payload = FALLBACK_BUILDERS[target](markdown, source_url)
        schema_cls = TARGET_SCHEMAS[target]
        try:
            return schema_cls.model_validate(payload)
        except ValidationError as exc:
            # A fallback should degrade, never explode: report honestly.
            logger.error("Fallback payload rejected for %s: %s", target.value, exc)
            minimal = schema_cls.model_validate(
                {
                    "missing_fields": ["all"],
                    "warnings": [
                        "fallback failed: " + "; ".join(
                            f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}"
                            for e in exc.errors()[:5]
                        )
                    ],
                }
            )
            return minimal


FALLBACK_BUILDERS: dict[ExtractionTarget, Callable[..., dict]] = {
    ExtractionTarget.PRICING_MATRIX: ph.fallback_pricing_matrix,
    ExtractionTarget.FEATURE_COMPARISON: ph.fallback_feature_comparison,
    ExtractionTarget.MARKET_NEWS: ph.fallback_market_news,
    ExtractionTarget.SENTIMENT_SCORE: ph.fallback_sentiment_score,
}
