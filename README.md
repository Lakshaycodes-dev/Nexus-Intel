# Nexus-Intel

Competitor intelligence pipeline built on TinyFish Search, Web Agent, and Fetch.

## Setup

```bash
python -m pip install -r requirements.txt
copy .env.example .env
```

Set `TINYFISH_API_KEY` in `.env`. Keep `MOCK_MODE=true` to run without a key or
network calls. Never commit `.env`.

## Run the pipeline

```bash
python orchestrator.py
```

The pipeline searches for competitor URLs, asks the TinyFish Web Agent for
structured intelligence, fetches Markdown for the same URLs, and writes a report
under `output/`.

## Web Agent

```python
import asyncio

from services.tinyfish_agent import run_web_agent


async def main() -> None:
    result = await run_web_agent(
        "https://stripe.com/pricing",
        "Extract current plans, prices, features, and recent product announcements.",
    )
    print(result.as_dict()["session_id"])
    print(result.as_dict()["data"])


asyncio.run(main())
```

`run_web_agent(competitor_or_url, objective, *, website_url=None, ...)` accepts a
URL or domain. A plain competitor name requires `website_url`.

The returned `WebAgentResult` exposes:

- `session_id`: populated only when TinyFish explicitly returns a browser session identifier.
- `session_id_missing_reason`: explains why it is `None`.
- `run_id` / `run_ids`: TinyFish Agent run identifiers for audit and support.
- `data`: structured pricing, features, product details, announcements, sources,
  missing data, and unverified claims.
- `success`, `status`, `errors`, `last_error`, `attempts`, and `duration_seconds`.

The current TinyFish Agent API returns `run_id` (and `streaming_url` while
running), not a browser `session_id`. The module therefore never invents one.
The public Fetch API is stateless and does not accept an Agent session, so Fetch
always performs a fresh render. The orchestrator passes the field through when it
is present and otherwise records the explicit missing-session reason.

## Tests

```bash
python -m unittest discover -s tests -v
```

Tests use mocked TinyFish responses and do not require an API key.
