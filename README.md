🚀 Nexus Intel
Autonomous B2B Market & Competitor Intelligence Platform

Built for KriticalHacks 2026 by Mutex Cartel

Tracking competitor pricing changes, stealth feature launches, and hidden site updates manually takes hours of tedious research. Nexus Intel is an autonomous AI intelligence platform that reduces hours of manual competitive research down to just 30 seconds (~480x faster).

By leveraging advanced web agents and large language models, Nexus Intel autonomously navigates competitor sites, clicks through complex pricing toggles, and synthesizes the data into structured, actionable market reports.

✨ Key Technical Features
Autonomous DOM Navigation: Utilizes TinyFish Web Agents to interact with complex web pages (clicking "Annual Billing" toggles, expanding hidden feature accordions) prior to extraction.

Stateful Data Extraction: Maintains browser session state (session_id) between the Web Agent navigation and the Fetch API, ensuring we extract the modified DOM rather than a default page load.

Structured AI Synthesis: Passes raw markdown into Gemini 1.5 Flash with strict Pydantic schemas to output clean, reliable JSON data for the frontend dashboard.

Serverless & Scalable Architecture: Built to operate with zero idle server costs, utilizing highly efficient, asynchronous pipeline execution.

🛠️ Tech Stack
Core Pipeline: Python, asynchronous execution (asyncio)

Web Agent & Extraction: TinyFish API (Search, Agent Navigation, Fetch)

LLM Synthesis: Google Gemini 1.5 Flash

Backend Framework: FastAPI

Database: MongoDB Atlas

Frontend: Next.js, TailwindCSS (Connected via REST endpoints)

💻 Local Setup & Installation (For Judges & Devs)
1. Clone the repository

## FastAPI backend (`app/`)

HTTP layer that lets the frontend trigger the existing orchestrator pipeline,
persist the run in MongoDB, and retrieve results later. The pipeline itself
(`orchestrator.py` -> `services/` -> `schemas/` -> `utils/`) is untouched; the
backend only wraps `async run_pipeline(query, mock) -> Path`.

| Module | Responsibility |
| --- | --- |
| `app/main.py` | App factory, CORS, lifespan (Mongo connect/close), `GET /health`, Swagger at `/docs` |
| `app/config.py` | Env-driven settings (`os.getenv` + `python-dotenv`, same convention as `config.py`) |
| `app/database.py` | Motor async client, index creation, `AnalysisRepository` (all persistence lives here) |
| `app/security.py` | Domain normalisation (frontend parity) + SSRF guards (blocks localhost, private/internal IPs, internal TLDs, non-http(s) schemes, embedded credentials) |
| `app/errors.py` | Uniform error envelope `{"error": {code, message, details}}` + exception handlers (never leaks stack traces, DSNs or keys) |
| `app/schemas.py` | Request/response contracts, incl. the frontend's `CompetitorData` shape |
| `app/services/orchestrator_service.py` | Calls the real `run_pipeline`, runs `GeminiService` extraction in a worker thread (`asyncio.to_thread`), maps `PricingMatrix`/`MarketNews`/`FeatureComparison` -> `CompetitorData` |
| `app/routers/analyze.py` | `POST /api/v1/analyze`, `GET /api/v1/analyze/{analysis_id}` |
| `app/routers/competitors.py` | `GET /api/v1/competitors/{id}` |
| `tests/test_api.py` | 25 offline API tests (fake repository + stubbed pipeline) |
| `scripts/smoke_test.py` | 17-check live smoke test against a running server |

### Install and run

```bash
python -m venv .venv && .venv\Scripts\activate   # or activate on your platform
pip install -r requirements.txt
# .env: copy .env.example -> .env and fill in values (never commit .env)
uvicorn app.main:app --reload --port 8000
```

- Swagger UI: <http://localhost:8000/docs> · ReDoc: `/redoc` · OpenAPI: `/openapi.json`
- Run from the repository root so `app` (and the pipeline modules it imports) resolve.

### Environment variables (see `.env.example`)

| Variable | Default | Purpose |
| --- | --- | --- |
| `MONGODB_URI` | `mongodb://localhost:27017` | Connection string (never logged or echoed) |
| `MONGODB_DATABASE` / `MONGODB_COLLECTION` | `nexus_intel` / `analyses` | Where analysis records are stored |
| `MONGODB_SERVER_SELECTION_TIMEOUT_MS` | `2000` | Startup probe timeout; app still boots if Mongo is down |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated allowed origins |
| `CORS_ALLOW_CREDENTIALS` | `false` | Credentialled CORS (off: no auth is used) |
| `ANALYSIS_TIMEOUT_SECONDS` | `300` | Hard timeout around one pipeline run -> 504 |
| `MOCK_MODE` | `true` | Passed through to `run_pipeline(query, mock)` per request unless overridden |

### Endpoints

All errors share one envelope: `{"error": {"code": "not_found", "message": "...", "details": [...]}}`
(codes: `validation_error` 422, `not_found` 404, `pipeline_failed` 502,
`analysis_timeout` 504, `database_unavailable` 503, `internal_error` 500).

**`POST /api/v1/analyze`** — triggers the pipeline and returns the finished result
(the orchestrator is async, so awaiting it in-request does not block the event loop;
`GeminiService` extraction runs via `asyncio.to_thread`).

```json
{
  "domain": "stripe.com",
  "parameters": {"pricing_tiers": true, "feature_accordions": true, "offsite_mentions": true},
  "query": null,
  "mock": null
}
```

`domain` accepts a bare domain or a full URL (normalised like the frontend:
`https://www.stripe.com/pricing` -> `stripe.com`). `query` and `mock` are optional
overrides. Response 200:

```json
{
  "analysis_id": "4a7bb1f3f45c4402a3dcda672a65cf70",
  "status": "completed",
  "domain": "stripe.com",
  "query": "stripe pricing",
  "mock": true,
  "created_at": "2026-10-20T18:00:00Z",
  "completed_at": "2026-10-20T18:00:02Z",
  "execution_time_sec": 1.9,
  "report_path": "output/stripe_pricing_market_intelligence.md",
  "extractions": [{"target": "pricing_matrix", "provenance": null, "missing_fields": [], "warnings": [], "error": null}],
  "data": {
    "domain": "stripe.com",
    "pricing": [{"tier": "Starter", "monthly": "$0", "annual": "", "features": ["1", "Basic dashboard and email support"]}],
    "offsiteNews": [{"title": "...", "source": "TechCrunch", "url": "https://...", "sentiment": "neutral"}],
    "capabilities": [{"name": "...", "traditionalScraper": false, "nexusIntel": true}],
    "executionTimeSec": 1.9
  }
}
```

`data` matches the frontend's `CompetitorData` validator exactly
(`domain: string`, three arrays, `executionTimeSec: number`).

**`GET /api/v1/analyze/{analysis_id}`** — status/result of one run
(`queued` -> `running` -> `completed` | `failed`, with `data`, `extractions`,
timestamps and a client-safe `error` on failure). 404 if unknown.

**`GET /api/v1/competitors/{id}`** — `{id}` is *either* a competitor domain
(`stripe.com`, URLs are normalised) *or* a 32-char `analysis_id`; returns the
matching record (latest analysis for that domain) with `competitor_id`, `domain`,
`analysis_id`, `status`, `data`. 404 if nothing matches.

**`GET /health`** — `{"status": "ok"|"degraded", "database": "connected"|"unavailable",
"mock_mode": true, "version": "1.0.0", ...}`; never exposes the connection string.
The app boots even when MongoDB is down (persistence endpoints then return 503).

### Tests

```bash
python -m pytest tests/ -v          # 25 API tests + 28 pipeline tests (53 total)
python scripts/smoke_test.py        # 17 live checks against http://127.0.0.1:8000
```

Tests are fully offline: MongoDB is replaced with an in-memory fake repository
(dependency override) and the orchestrator service is monkeypatched.

### Notes and assumptions

- The pipeline is **query**-based; the frontend contract sends a **domain**. The
  backend derives the query (`"stripe.com"` -> `"stripe pricing"`) unless an
  explicit `query` is supplied. Documented, not invented elsewhere.
- There is no separate competitor collection: a competitor is identified by its
  normalised domain, and `{id}` lookup falls back from `analysis_id` to
  "latest analysis for that domain".
- `POST /analyze` awaits the pipeline inline because the existing frontend reads
  the finished payload from the POST response; the persisted record keeps
  `GET /analyze/{id}` useful for re-checks and polling.
- The pipeline writes `output/<slug>.md` per query; concurrent runs of the
  *same* query share that file (pre-existing orchestrator behaviour, unchanged).
- The heuristic fallback parser can emit non-enum `billing_period` values
  (e.g. `"$0"`); the API maps anything that is not a recognised annual period
  to the monthly column and drops duplicate price cells from `features`.
