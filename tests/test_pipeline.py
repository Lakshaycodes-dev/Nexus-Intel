"""Offline test-suite for the LLM extraction pipeline.

Runs without network access or API credentials: the Gemini client is replaced by
a stub that returns canned responses, exercising the same code path the real
service uses (prompt -> structured output -> validation -> repair -> fallback).

Run with either:
    python -m unittest discover -s tests -v
    python tests/test_pipeline.py
"""

from __future__ import annotations

import json
import os
import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from schemas.pydantic_schemas import (  # noqa: E402
    FeatureComparison,
    MarketNews,
    PricingMatrix,
    SentimentScore,
    TARGET_SCHEMAS,
    ExtractionTarget,
)
from services.gemini_service import GeminiService, build_prompt  # noqa: E402
from utils import parser_helpers as ph  # noqa: E402


SAMPLE_PRICING_MD = """\
# TinyFish Pricing

## Plans
| Plan | Price | Billing | Seats |
| --- | --- | --- | --- |
| Starter | $49/mo | monthly | 1 |
| Pro | $199/mo | monthly | 5 |
| Enterprise | Contact sales | custom | - |

## Metered usage
| Metric | Rate | Unit |
| --- | --- | --- |
| Input tokens | $0.50 | per 1M tokens |
| Requests | $2.00 | per 1K requests |

Also includes a **free tier** with 100 requests/day.
"""

SAMPLE_NEWS_MD = """\
# AI API Market News

- [TinyFish raises $20M Series A](https://example.com/tinyfish-series-a) Oct 12, 2025 - funding round led by Atlas.
- [RivalCorp launches cheap inference API](https://example.com/rivalcorp) 2025-10-01

## Announcements
### TinyFish ships Realtime API
"""


class StubClient:
    """Mimics ``client.models.generate_content`` with scripted responses."""

    def __init__(self, payloads: list[str]):
        self.payloads = list(payloads)
        self.calls: list[dict] = []
        self.models = SimpleNamespace(generate_content=self._generate)

    def _generate(self, *, model, contents, config):  # noqa: ANN001
        self.calls.append({"model": model, "contents": contents, "config": config})
        payload = self.payloads.pop(0) if self.payloads else "{}"
        return SimpleNamespace(parsed=None, text=payload, candidates=[])


def make_service(payloads: list[str], **kwargs) -> GeminiService:
    return GeminiService(client=StubClient(payloads), sleep=lambda _s: None, **kwargs)


# --------------------------------------------------------------------------- #
class TestSchemas(unittest.TestCase):
    def test_pricing_valid_roundtrip(self):
        instance = PricingMatrix.model_validate(
            {
                "vendor": "TinyFish",
                "currency": "usd",
                "plans": [
                    {"name": "Starter", "price": "$49", "price_display": "$49/mo"},
                    {"name": "Legacy", "price": "n/a"},
                ],
            }
        )
        self.assertEqual(instance.currency, "USD")
        self.assertEqual(instance.plans[0].price, 49.0)
        self.assertIsNone(instance.plans[1].price)

    def test_extra_keys_rejected(self):
        with self.assertRaises(Exception):
            PricingMatrix.model_validate({"plans": [], "surprise": 1})

    def test_sentiment_score_clamped_and_labelled(self):
        instance = SentimentScore.model_validate(
            {"overall_score": "0.75", "label": "Pos", "confidence": 0.9}
        )
        self.assertEqual(instance.overall_score, 0.75)
        self.assertEqual(instance.label.value, "positive")

    def test_sentiment_score_out_of_range_rejected(self):
        with self.assertRaises(Exception):
            SentimentScore.model_validate({"overall_score": 5, "label": "positive"})

    def test_news_unparseable_date_kept_raw(self):
        instance = MarketNews.model_validate(
            {"items": [{"title": "T", "published_date": "sometime last Tuesday"}]}
        )
        self.assertIsNone(instance.items[0].published_date)
        self.assertEqual(instance.items[0].published_date_raw, "sometime last Tuesday")

    def test_news_iso_date_parsed(self):
        instance = MarketNews.model_validate(
            {"items": [{"title": "T", "published_date": "2025-10-12T09:00:00"}]}
        )
        self.assertEqual(str(instance.items[0].published_date), "2025-10-12")

    def test_every_target_registers_a_schema(self):
        for target in ExtractionTarget:
            self.assertIn(target, TARGET_SCHEMAS)


# --------------------------------------------------------------------------- #
class TestParserHelpers(unittest.TestCase):
    def test_clean_markdown_strips_fences_and_html(self):
        cleaned = ph.clean_markdown("```json\n{...}\n```\n<b>hi</b>  world")
        self.assertNotIn("```", cleaned)
        self.assertNotIn("<b>", cleaned)
        self.assertIn("hi world", cleaned)

    def test_table_parsing(self):
        tables = list(ph.iter_markdown_tables(SAMPLE_PRICING_MD))
        self.assertEqual(len(tables), 2)
        records = ph.table_to_records(tables[0])
        self.assertEqual(records[0]["Plan"], "Starter")
        self.assertEqual(records[2]["Price"], "Contact sales")

    def test_detect_layout(self):
        self.assertEqual(ph.detect_layout(SAMPLE_PRICING_MD), "tables")
        self.assertEqual(ph.detect_layout(""), "empty")
        self.assertEqual(ph.detect_layout("Just a single sentence of prose."), "prose")

    def test_extract_json_block_from_noisy_text(self):
        noisy = 'Sure! Here is the JSON:\n```json\n{"a": {"b": 1}}\n```\nHope that helps.'
        self.assertEqual(json.loads(ph.extract_json_block(noisy)), {"a": {"b": 1}})

    def test_loads_lenient_tolerates_trailing_commas(self):
        self.assertEqual(ph.loads_lenient('{"a": 1,}'), {"a": 1})

    def test_parse_money(self):
        self.assertEqual(ph.parse_money("$1,299/yr")["amount"], 1299.0)
        self.assertEqual(ph.parse_money("$0.50")["currency"], "USD")
        self.assertEqual(ph.parse_money("12k")["amount"], 12000.0)
        self.assertIsNone(ph.parse_money("contact us"))

    def test_parse_bool_token(self):
        self.assertIs(ph.parse_bool_token("✓"), True)
        self.assertIs(ph.parse_bool_token("no"), False)
        self.assertIsNone(ph.parse_bool_token("—"))
        self.assertIsNone(ph.parse_bool_token("n/a"))


# --------------------------------------------------------------------------- #
class TestFallbacks(unittest.TestCase):
    def test_pricing_fallback(self):
        payload = ph.fallback_pricing_matrix(SAMPLE_PRICING_MD, "https://tiny.fish/pricing")
        instance = PricingMatrix.model_validate(payload)
        names = [p.name for p in instance.plans]
        self.assertIn("Starter", names)
        self.assertIn("Enterprise", names)
        starter = next(p for p in instance.plans if p.name == "Starter")
        self.assertEqual(starter.price, 49.0)
        self.assertEqual(starter.billing_period.value, "monthly")
        self.assertEqual(len(instance.usage_based_rates), 2)
        self.assertIsNotNone(instance.free_tier)
        self.assertEqual(instance.source_url, "https://tiny.fish/pricing")

    def test_feature_fallback(self):
        md = (
            "## Security\n"
            "| Feature | TinyFish | Rival |\n| --- | --- | --- |\n"
            "| SSO | ✓ | ✗ |\n| Audit logs | - | Yes |\n"
        )
        payload = ph.fallback_feature_comparison(md)
        instance = FeatureComparison.model_validate(payload)
        sso = instance.categories[0].features[0]
        self.assertEqual(sso.support.value, "supported")
        audit = instance.categories[0].features[1]
        self.assertEqual(audit.support.value, "unknown")  # "-" means unknown

    def test_news_fallback(self):
        payload = ph.fallback_market_news(SAMPLE_NEWS_MD, "https://example.com/news")
        instance = MarketNews.model_validate(payload)
        self.assertGreaterEqual(len(instance.items), 2)
        first = instance.items[0]
        self.assertEqual(first.url, "https://example.com/tinyfish-series-a")
        self.assertEqual(str(first.published_date), "2025-10-12")
        self.assertIn("TinyFish raises $20M Series A", [i.title for i in instance.items])

    def test_sentiment_fallback(self):
        positive = (
            "# Review\n## Performance\nFast and reliable, excellent latency.\n"
            "## Pricing\nAffordable and generous free tier.\n"
        )
        instance = SentimentScore.model_validate(ph.fallback_sentiment_score(positive))
        self.assertGreater(instance.overall_score, 0)
        self.assertEqual(instance.label.value, "positive")
        self.assertGreaterEqual(len(instance.aspects), 2)

    def test_empty_markdown_still_valid(self):
        for target in ExtractionTarget:
            payload = {"missing_fields": ["all"], "warnings": ["empty"]}
            if target is not ExtractionTarget.SENTIMENT_SCORE:
                TARGET_SCHEMAS[target].model_validate(payload)
        SentimentScore.model_validate(
            {"overall_score": 0.0, "label": "neutral", "confidence": 0.0}
        )


# --------------------------------------------------------------------------- #
class TestPromptEngineering(unittest.TestCase):
    def test_prompt_contains_contract_and_source(self):
        prompt = build_prompt(
            ExtractionTarget.PRICING_MATRIX,
            "| Plan | Price |\n| --- | --- |\n| Pro | $9 |",
            source_url="https://x.test/pricing",
            layout="tables",
        )
        self.assertIn("PricingMatrix", prompt)
        self.assertIn('"target" value: "pricing_matrix"', prompt)
        self.assertIn("EXTRACT, NEVER INVENT", __import__("services.gemini_service", fromlist=["x"])._SYSTEM_INSTRUCTION)
        self.assertIn("<markdown>", prompt)
        self.assertIn("https://x.test/pricing", prompt)

    def test_repair_prompt_lists_validation_errors(self):
        prompt = build_prompt(
            ExtractionTarget.MARKET_NEWS,
            "# news",
            validation_errors=["items.0.title: Field required"],
        )
        self.assertIn("failed validation", prompt)
        self.assertIn("items.0.title", prompt)


# --------------------------------------------------------------------------- #
class TestServicePipeline(unittest.TestCase):
    def test_happy_path_returns_valid_instance(self):
        good = json.dumps(
            {
                "target": "pricing_matrix",
                "vendor": "TinyFish",
                "currency": "USD",
                "plans": [{"name": "Pro", "price": 199, "billing_period": "monthly"}],
                "usage_based_rates": [],
                "missing_fields": [],
                "warnings": [],
            }
        )
        service = make_service([good])
        result = service.extract_pricing(SAMPLE_PRICING_MD, source_url="https://tiny.fish")
        self.assertIsInstance(result, PricingMatrix)
        self.assertEqual(result.plans[0].price, 199.0)
        self.assertEqual(len(service._client.calls), 1)
        # Structured-output config must be attached to the call.
        call = service._client.calls[0]
        self.assertEqual(call["config"].response_mime_type, "application/json")
        self.assertIs(call["config"].response_schema, PricingMatrix)

    def test_invalid_output_triggers_repair_then_success(self):
        bad = json.dumps({"target": "pricing_matrix", "plans": [{"name": "Pro", "price": "abc"}], "surprise": 1})
        good = json.dumps(
            {"target": "pricing_matrix", "plans": [{"name": "Pro", "price": 12.5}]}
        )
        service = make_service([bad, good])
        result = service.extract_pricing(SAMPLE_PRICING_MD)
        self.assertEqual(result.plans[0].price, 12.5)
        self.assertEqual(len(service._client.calls), 2)
        self.assertIn("repaired:", " ".join(result.warnings))
        # Repair prompt must carry the first response's validation errors.
        self.assertIn("failed validation", service._client.calls[1]["contents"])

    def test_all_attempts_invalid_falls_back_to_heuristics(self):
        service = make_service(["not json at all", "still not json"])
        result = service.extract_pricing(SAMPLE_PRICING_MD, source_url="https://tiny.fish")
        self.assertIsInstance(result, PricingMatrix)
        self.assertTrue(any("fallback" in w for w in result.warnings))
        self.assertEqual(len(service._client.calls), 2)  # LLM tried, then gave up
        self.assertTrue(result.plans)

    def test_missing_api_key_degrades_to_fallback(self):
        service = GeminiService(client=None, api_key=None, sleep=lambda _s: None)
        os.environ.pop("GEMINI_API_KEY", None)
        os.environ.pop("GOOGLE_API_KEY", None)
        result = service.extract_pricing(SAMPLE_PRICING_MD)
        self.assertIsInstance(result, PricingMatrix)
        self.assertTrue(result.plans)

    def test_empty_input_skips_api(self):
        service = make_service([])
        result = service.extract_pricing("   \n\n  ")
        self.assertIsInstance(result, PricingMatrix)
        self.assertEqual(service._client.calls, [])
        self.assertIn("empty input markdown", result.warnings[0])

    def test_sentiment_target_via_string(self):
        service = make_service([json.dumps({"overall_score": 0.4, "label": "positive", "confidence": 0.8})])
        result = service.extract("sentiment_score", "# Great product\nI love it.")
        self.assertIsInstance(result, SentimentScore)
        self.assertEqual(result.overall_score, 0.4)

    def test_unparseable_error_message_surfaces_in_repair(self):
        service = make_service(["Here you go: ```json {bad json```", json.dumps({"target": "market_news", "items": []})])
        result = service.extract_news("# News")
        self.assertIsInstance(result, MarketNews)
        self.assertEqual(len(service._client.calls), 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
