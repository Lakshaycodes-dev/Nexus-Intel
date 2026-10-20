# Nexus-Intel

## Gemini extraction module

Turns raw TinyFish web markdown into strict, validated JSON.

| Module | Responsibility |
| --- | --- |
| `services/gemini_service.py` | Gemini 1.5 Flash integration, prompt engineering, schema-constrained output, repair loop, heuristic fallback |
| `schemas/pydantic_schemas.py` | Strict Pydantic contracts: `PricingMatrix`, `FeatureComparison`, `MarketNews`, `SentimentScore` |
| `utils/parser_helpers.py` | Markdown normalisation, table/value parsing, fallback extractors |
| `tests/test_pipeline.py` | Offline test suite (no API key required) |

```python
from services.gemini_service import GeminiService

svc = GeminiService()                      # reads GEMINI_API_KEY via os.getenv()
pricing = svc.extract_pricing(markdown, source_url="https://vendor/pricing")
print(pricing.model_dump_json(indent=2))
```

Pipeline: normalise markdown -> Gemini structured output (`response_schema`)
-> validation -> repair pass with error feedback -> heuristic fallback.
Missing values are never invented: they land in `missing_fields`, with parse
issues in `warnings`.

Configuration (`.env`, see `.env.example`): `GEMINI_API_KEY`, `GEMINI_MODEL`
(default `gemini-1.5-flash`).

```bash
python -m unittest discover -s tests -v
```
