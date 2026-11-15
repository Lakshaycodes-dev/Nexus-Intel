## Nexus Intel

**AI-powered B2B market intelligence.** Nexus Intel crawls competitor websites, extracts pricing, packaging, capabilities and market signals, and turns the result into a dashboard your team can act on.

---

## Why it exists

Most competitive research is still a spreadsheet and a browser tab. Nexus Intel automates the loop:

1. **Discover** the pages that matter (pricing, features, changelog, announcements).
2. **Render** them in a real browser so JavaScript-heavy sites work.
3. **Extract** structured intelligence with an LLM and schema validation.
4. **Track** what changed since the previous run.
5. **Compare** competitors side by side in a modern dashboard.

---

##  Features

| Area | What it does |
| --- | --- |
| **Playwright collection** | Discovers pricing, feature, changelog and announcement pages via `robots.txt`, sitemaps and internal links, then renders them with headless Chromium. |
| **Bounded interaction** | Safely dismisses overlays and captures monthly/annual billing states without clicking destructive actions. |
| **Incremental tracking** | Stores page snapshots, content hashes and structured change events, so repeat runs reuse recent content and report plan/price/feature changes. |
| **LLM synthesis** | Google Gemini extracts schema-validated intelligence from the generated Markdown report, with a repair pass, deterministic fallbacks and per-field provenance. |
| **Async pipeline** | FastAPI keeps long collection runs off the event loop; every run is persisted with `queued → running → completed / failed` transitions. |
| **Private workspaces** | Email + password accounts, scrypt password hashing, HS256 JWTs, and per-user data scoping on every analysis endpoint. |
| **Modern dashboard** | Next.js + TailwindCSS UI for market overview, competitor briefs, pricing matrices, feature accordions, signal feeds and a comparison workspace. |
| **Safe by default** | SSRF guards block private/internal hosts, `robots.txt` is respected, crawl depth/page counts are bounded, and mock mode works fully offline. |

---

##  Architecture

```text
┌──────────────────────┐        ┌───────────────────────────────┐
│  Next.js 16 client   │  HTTP  │        FastAPI backend        │
│  (client/)           │ ─────► │        (app/)                 │
│  • marketing + auth  │        │  • /api/v1/auth/*             │
│  • dashboard         │        │  • /api/v1/analyze            │
│  • comparison        │        │  • /api/v1/competitors        │
└──────────────────────┘        └──────────────┬────────────────┘
                                               │
                                ┌──────────────▼────────────────┐
                                │  Orchestrator + collection    │
                                │  (orchestrator.py, services/) │
                                │                               │
                                │  discovery → Playwright →     │
                                │  extraction → tracking →      │
                                │  Markdown + JSON report       │
                                └───────┬───────────────┬───────┘
                                        │               │
                                ┌───────▼──────┐  ┌─────▼────────┐
                                │  MongoDB     │  │ Google Gemini │
                                │  (persistence│  │ (LLM extract) │
                                │  + tracking) │  └──────────────┘
                                └──────────────┘
```

### Tech stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js 16, React 19, TailwindCSS 3, TypeScript 5, Framer Motion, Recharts, Lucide |
| Backend | Python, FastAPI, Uvicorn, Pydantic v2 |
| Collection | Playwright (Chromium), httpx, `robots.txt` / sitemap discovery |
| Database | MongoDB Atlas or local MongoDB (motor async driver) |
| AI | Google Gemini via `google-genai` |
| Auth | Stdlib `hashlib.scrypt` + HS256 JWTs (no third-party auth dependency) |
| Tests | pytest + FastAPI `TestClient`, fully offline |

---

##  Repository layout

```text
Nexus-Intel/
├── app/                          # FastAPI backend
│   ├── main.py                   # App entry point, CORS, health check
│   ├── config.py                 # Backend env configuration
│   ├── database.py               # Mongo repositories + in-memory fallback
│   ├── schemas.py                # API request/response contracts
│   ├── security.py               # Domain normalisation + SSRF guards
│   ├── errors.py                 # Error envelopes and exception handlers
│   ├── auth/                     # scrypt hashing, JWT tokens, dependencies
│   ├── routers/                  # auth, analyze, competitors
│   └── services/                 # API ↔ pipeline adapter
├── services/
│   ├── collection/               # Discovery, browser, extraction, tracking
│   └── gemini_service.py         # Gemini extraction + heuristic fallback
├── schemas/                      # Pydantic extraction contracts
├── utils/                        # Markdown parsing helpers
├── orchestrator.py               # Directly runnable collection entry point
├── config.py                     # Root runtime config (MOCK_MODE, etc.)
├── scripts/smoke_test.py         # Live API smoke test
├── tests/                        # Offline pytest suite
├── output/                       # Generated Markdown + JSON reports
├── client/                       # Next.js frontend
│   ├── app/(marketing)/          # Landing page
│   ├── app/(auth)/               # /login and /signup
│   ├── app/dashboard/            # Overview, compare, competitor briefs
│   ├── components/               # UI + dashboard components
│   └── lib/                      # API client, adapters, auth, fixtures
├── requirements.txt
└── README.md
```

---

##  Prerequisites

- **Python 3.10+**
- **Node.js 20.9+** and npm (required by Next.js 16)
- **MongoDB** (optional for local demos — see [Mock vs. live](#-mock-vs-live-mode))
- **Google Gemini API key** (optional; heuristics run without one)
- Chromium binaries for Playwright (installed in the setup step below)

---

##  Quick start

### 1. Backend (FastAPI)

From the repository root:

```bash
python -m venv venv

# Windows (PowerShell / cmd)
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate

pip install -r requirements.txt
playwright install chromium

cp .env.example .env        # Windows: copy .env.example .env
uvicorn app.main:app --reload --port 8000
```

- API: <http://localhost:8000>
- Swagger UI: <http://localhost:8000/docs>
- Health: <http://localhost:8000/health>

The app boots even when MongoDB is unreachable. With `MOCK_MODE=true` (the default), persistence and tracking fall back to an in-process store, so the whole pipeline works offline with deterministic mock pages.

Run the collection pipeline directly (no server required):

```bash
python orchestrator.py
```

### 2. Frontend (Next.js)

In a second terminal:

```bash
cp client/.env.example client/.env.local     # Windows: copy client\.env.example client\.env.local
cd client
npm install
npm run dev
```

Open <http://localhost:3000>.

The dashboard is browsable as a demo without an account. Sign up at <http://localhost:3000/signup> to run live scans and save results to your workspace.

> The browser calls the API directly, so keep `CORS_ORIGINS` aligned with the frontend origin. The defaults allow `http://localhost:3000` and `http://127.0.0.1:3000`.

---

##  Configuration

Copy `.env.example` to `.env` at the repository root. Never commit real keys.

### Core runtime

| Variable | Default | Purpose |
| --- | --- | --- |
| `MOCK_MODE` | `true` | Run the full pipeline offline with deterministic pages. |
| `GEMINI_API_KEY` | — | Google Gemini API key. Without it, heuristic extraction is used. |
| `GEMINI_MODEL` | `gemini-3.8-flash` | Gemini model for structured extraction. |
| `MONGODB_URI` | `mongodb://localhost:27017` | MongoDB connection string. |
| `MONGODB_DATABASE` | `nexus_intel` | Database name. |
| `MONGODB_COLLECTION` | `analyses` | Analysis records. |
| `IN_MEMORY_PERSISTENCE` | `true` in mock mode | Keep records in process memory when MongoDB is unavailable; resets on restart. |
| `CORS_ORIGINS` | `http://localhost:3000,http://127.0.0.1:3000` | Comma-separated allowed frontend origins. |
| `ANALYSIS_TIMEOUT_SECONDS` | `300` | Hard timeout around one analysis run. |

### Authentication

| Variable | Default | Purpose |
| --- | --- | --- |
| `JWT_SECRET` | ephemeral | Token signing key. **Set this in any real deployment**; otherwise sessions reset on restart. |
| `JWT_EXPIRES_MINUTES` | `10080` (7 days) | Access-token lifetime. |
| `PASSWORD_MIN_LENGTH` | `8` | Minimum password length (enforced at ≥ 8). |
| `ALLOW_REGISTRATION` | `true` | Set to `false` to close public sign-ups. |
| `MONGODB_USERS_COLLECTION` | `users` | Account records. |

Generate a signing key:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

### Collection & tracking

All values are optional and documented in `.env.example`:

| Group | Variables |
| --- | --- |
| Browser | `PLAYWRIGHT_BROWSER`, `PLAYWRIGHT_HEADLESS`, `PLAYWRIGHT_USER_AGENT`, `PLAYWRIGHT_VIEWPORT_WIDTH`, `PLAYWRIGHT_VIEWPORT_HEIGHT`, `PLAYWRIGHT_BLOCK_RESOURCES`, `PLAYWRIGHT_ALLOW_STATIC_FALLBACK` |
| Timeouts | `NAVIGATION_TIMEOUT_MS`, `INTERACTION_TIMEOUT_MS`, `PAGE_SETTLE_TIMEOUT_MS` |
| Crawl | `MAX_PAGES_PER_COMPETITOR`, `CRAWL_MAX_DEPTH`, `CRAWL_CONCURRENCY`, `CRAWL_REQUEST_TIMEOUT_SECONDS`, `CRAWL_INTERVAL_SECONDS`, `CRAWL_RESPECT_ROBOTS` |
| Interaction | `MAX_INTERACTIONS`, `CAPTURE_BILLING_STATES` |
| Tracking | `TRACKING_ENABLED`, `TRACKING_INCREMENTAL_CRAWL`, `TRACKING_INTERVAL_HOURS`, `TRACKING_STORE_FULL_SNAPSHOT` |
| Limits | `COLLECTION_MAX_HTML_CHARS`, `COLLECTION_MAX_TEXT_CHARS`, `COLLECTION_ALLOW_PRIVATE_HOSTS` |

> `COLLECTION_ALLOW_PRIVATE_HOSTS` exists for tests only. Never enable it in production.

### Optional company-name resolution

If a user supplies a company name without a domain, configure a search provider:

```dotenv
SEARCH_PROVIDER=gemini            # uses GEMINI_API_KEY
# or
SEARCH_PROVIDER=http              # uses SEARCH_API_URL + SEARCH_API_KEY (Serper-compatible)
SEARCH_API_URL=
SEARCH_API_KEY=
SEARCH_MAX_RESULTS=5
```

### Frontend

`client/.env.local`:

```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

---

##  Authentication & workspaces

Accounts are email + password. Passwords are hashed with the stdlib `scrypt` KDF, and sessions use HS256 JWTs signed by the API — no third-party auth service is required.

| Method | Endpoint | Auth | Purpose |
| --- | --- | --- | --- |
| `POST` | `/api/v1/auth/register` | — | Create an account and workspace; returns an access token (`201`). |
| `POST` | `/api/v1/auth/login` | — | Sign in with email + password. |
| `GET` | `/api/v1/auth/me` | Bearer | Return the signed-in profile. |
| `POST` | `/api/v1/auth/logout` | — | Stateless sign-out helper (`204`); the client discards its token. |

Every analysis endpoint requires `Authorization: Bearer <token>` and filters records by `user_id`, so one workspace can never read another's data. On the frontend, the token is stored in `localStorage` and mirrored into a same-origin cookie so React Server Components can read competitor briefs. This is convenient for a hackathon build; move to an `httpOnly` cookie plus a route handler before production if XSS is a concern.

### Example flow

```bash
# 1. Register (or /login) and copy the access_token
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Lakshay Sharma","email":"lakshay@example.com","password":"correct-horse-battery"}'

# 2. Run a scan in your workspace
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"domain":"stripe.com","parameters":{"pricing_tiers":true,"feature_accordions":true,"offsite_mentions":true}}'
```

---

##  API reference

Base URL: `http://localhost:8000`

| Method | Endpoint | Auth | Description |
| --- | --- | --- | --- |
| `GET` | `/` | — | Service pointer (`/docs`, `/health`). |
| `GET` | `/health` | — | Liveness probe: `ok` or `degraded`, plus mock/database state. Never exposes credentials. |
| `GET` | `/docs` | — | Swagger UI (`/redoc`, `/openapi.json` also available). |
| `POST` | `/api/v1/analyze` | Bearer | Run the pipeline for one competitor and persist the result. |
| `GET` | `/api/v1/analyze/{analysis_id}` | Bearer | Retrieve a stored analysis by 32-char ID (status, timestamps, results, error). |
| `GET` | `/api/v1/competitors` | Bearer | Latest run per tracked domain in your workspace. |
| `GET` | `/api/v1/competitors/{id}` | Bearer | One competitor brief by domain **or** analysis ID. |

### `POST /api/v1/analyze`

```json
{
  "domain": "stripe.com",
  "parameters": {
    "pricing_tiers": true,
    "feature_accordions": true,
    "offsite_mentions": true
  },
  "query": "stripe pricing",
  "mock": true
}
```

Only `domain` is required. `query` is derived from the domain when omitted, and `mock` defaults to the server's `MOCK_MODE`.

The response includes:

- `analysis_id`, `status`, timestamps and `execution_time_sec`
- `report_path` for the generated Markdown report
- `extractions[]` with `target`, `provenance` (`gemini` or `fallback`), `missing_fields`, `warnings` and `error`
- `data` in the frontend contract: `{ domain, pricing[], offsiteNews[], capabilities[], executionTimeSec, provenance }`

Errors use consistent envelopes: `422` for invalid input, `401` for missing/invalid tokens, `403` when registration is disabled, `409` for duplicate accounts, `404` for unknown records, `502` for pipeline failures, `503` when persistence is unavailable, and `504` for analysis timeouts.

---

##  How an analysis runs

```text
domain / query
   │
   ▼
1. Validate target            app/security.py — reject private/internal hosts
   │
   ▼
2. Resolve official domain    services/collection/domain_resolver.py
   │
   ▼
3. Discover pages             robots.txt → sitemaps → internal links, classified
   │                          as pricing / features / changelog / announcements
   ▼
4. Render + interact          Playwright Chromium, overlays dismissed, billing
   │                          states captured (monthly / annual), assets blocked
   ▼
5. Deterministic extraction   pricing, feature, announcement and generic extractors
   │
   ▼
6. Tracking                   content hash → snapshot → structured change events
   │
   ▼
7. Report                     output/<slug>_market_intelligence.md
   │                          + JSON sidecar with structured data & metadata
   ▼
8. LLM synthesis              Gemini structured output against Pydantic schemas,
   │                          with one repair pass and heuristic fallback
   ▼
9. Persist + return           MongoDB (or in-memory fallback) → API → dashboard
```

### Extraction safeguards

- Gemini is instructed to **extract, never invent**; values must be traceable to source text.
- Output is validated against strict Pydantic contracts in `schemas/pydantic_schemas.py`.
- A validation failure triggers a single repair call; if that fails, deterministic heuristics produce a valid result.
- Every extraction records provenance and `missing_fields`, so the UI can distinguish LLM output from fallbacks.

---

##  Mock vs. live mode

| | `MOCK_MODE=true` (default) | `MOCK_MODE=false` |
| --- | --- | --- |
| Pages | Deterministic mock snapshots | Real websites via Playwright |
| Network | Not required | Required |
| MongoDB | Optional; in-memory fallback | Required for persistence endpoints |
| Gemini | Optional; heuristics run | Recommended; heuristics still work |
| Best for | Local demos, tests, CI | Real market intelligence |

If Chromium is unavailable in live mode, the pipeline can fall back to static HTTP extraction (no JavaScript). This is clearly marked in the report. Set `PLAYWRIGHT_ALLOW_STATIC_FALLBACK=false` to fail loudly instead.

When MongoDB is unavailable and `IN_MEMORY_PERSISTENCE=true`, analyses and tracking state live in process memory so the dashboard and repeat-run change detection remain usable — everything resets when the server restarts. Set it to `false` outside local demos to require MongoDB.

---

##  Output artifacts

Each run writes to `output/`:

- `<slug>_market_intelligence.md` — human-readable report: per-source status, categories, billing states, retrieval mode, structured JSON blocks, crawl stats and detected changes.
- `<slug>_collection.json` — JSON sidecar with structured data and tracking metadata for auditability and downstream tooling.

A sample Stripe report is committed at `output/stripe_pricing_market_intelligence.md`.

---

##  Tests & checks

### Backend

```bash
python -m pytest tests/ -q
```

The suite is fully offline: mock pages and in-memory repositories are used, so no browser binaries, network, MongoDB or Gemini credentials are required. Coverage includes:

- API contracts, CORS, error envelopes and timeouts
- Auth: registration, login, token validation, workspace scoping
- Domain normalisation, SSRF guards, query derivation
- Collection: classification, canonicalisation, mock report + sidecar
- Tracking: snapshot reuse, change detection, layout-only noise filtering
- Domain resolution and aggregator rejection

### Live smoke test

With the backend running:

```bash
python scripts/smoke_test.py http://127.0.0.1:8000
```

It exercises `/health`, registration/login, an authenticated mock analysis, competitor lookup and error paths, exiting non-zero on the first failure.

### Frontend

```bash
cd client
npm run lint
npm run typecheck
npm run build
```

---

##  Troubleshooting

| Symptom | Fix |
| --- | --- |
| `playwright: Executable doesn't exist` | Run `playwright install chromium` inside the active virtualenv. |
| `/health` reports `degraded` / persistence returns `503` | MongoDB is unreachable. Start MongoDB, fix `MONGODB_URI`, or enable `IN_MEMORY_PERSISTENCE` for local demos. |
| `401 Unauthorized` on analysis calls | Sign in again; the JWT may be missing or expired. Tokens reset on backend restart unless `JWT_SECRET` is set. |
| Browser requests blocked by CORS | Add the frontend origin to `CORS_ORIGINS` and restart the API. |
| Gemini extraction falls back to heuristics | Check `GEMINI_API_KEY` / `GEMINI_MODEL`; inspect `extractions[].warnings` in the response. |
| `python` not found on Windows | Use `py -m venv venv` and `py -m pytest tests/ -q`. |
| Frontend can't reach the API | Verify `NEXT_PUBLIC_API_URL` in `client/.env.local` and that the backend is on port 8000. |
| Sign-ups fail with `403` | `ALLOW_REGISTRATION` is set to `false`. |

---

##  Safety & limitations

- `robots.txt` is respected by default (`CRAWL_RESPECT_ROBOTS=true`).
- Crawl depth, page count, concurrency and request rate are bounded.
- Interactions are limited to dismissals and non-destructive controls such as billing toggles.
- User-supplied targets are validated before navigation; private, loopback, link-local and internal hostnames are blocked.
- Only analyse sites you are permitted to access, and respect their terms of service.
- Auth tokens use a JS-readable cookie for server-component reads — harden this before production.
- No license file is included yet; add one before redistributing.

---

---

<p align="center"><em>Nexus Intel — know the market before it moves.</em></p>
