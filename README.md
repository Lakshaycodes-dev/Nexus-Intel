# 🌐 Nexus Intel
**AI-Powered B2B Market Intelligence Platform**

Nexus Intel is a full-stack platform designed for B2B Founders, Product Managers, and VCs to extract, synthesize, and act upon market data. Built by **Team Mutex Cartel** for KriticalHacks 2026.

## ✨ Key Features
* **Playwright Collection:** Discovers pricing, features, changelog and announcement pages via robots.txt, sitemaps and internal links, then renders them with headless Chromium.
* **Bounded Interaction:** Safely dismisses overlays and captures monthly/annual pricing states without clicking destructive actions.
* **Incremental Tracking:** Stores page snapshots and structured change events so repeat runs can reuse recent content and report plan/price/feature changes.
* **LLM Synthesis:** Google Gemini extracts schema-validated market intelligence from the generated Markdown report, with deterministic fallbacks.
* **Asynchronous Pipeline:** FastAPI backend keeps long collection runs off the event loop.
* **Modern Dashboard:** Next.js and TailwindCSS provide a responsive, real-time web interface.

## 🏗️ Architecture & Tech Stack
* **Frontend:** Next.js, TailwindCSS, React
* **Backend:** Python, FastAPI
* **Collection:** Playwright (Chromium), httpx, robots.txt/sitemap discovery
* **Database:** MongoDB Atlas (analyses + page registry, snapshots and change events)
* **AI:** Google Gemini

## 📂 Monorepo Structure
```text
Nexus-Intel/
├── client/                 # Next.js frontend
├── app/                    # FastAPI backend (routes, services, repository)
├── services/
│   ├── collection/         # Playwright discovery, browser, extraction, tracking
│   └── gemini_service.py   # LLM extraction + heuristic fallback
├── schemas/                # Pydantic extraction contracts
├── utils/                  # Markdown parsing helpers
├── orchestrator.py         # Directly runnable collection entry point
├── requirements.txt
└── README.md
```

## 🔐 Environment Variables
1. Backend (`/.env`, start from `.env.example`):
```dotenv
MOCK_MODE=true
GEMINI_API_KEY=your_google_gemini_key
MONGODB_URI=your_mongodb_connection_string
# Optional local fallback when MongoDB is unavailable (defaults to mock mode).
IN_MEMORY_PERSISTENCE=true

# Optional: resolve company names without a website URL
# SEARCH_PROVIDER=gemini   # uses GEMINI_API_KEY
# SEARCH_PROVIDER=http     # uses SEARCH_API_URL + SEARCH_API_KEY
```
2. Frontend (`/client/.env.local`):
```dotenv
NEXT_PUBLIC_API_URL=http://localhost:8000
```

## 🚀 Quick Setup
1. Backend (FastAPI)
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

pip install -r requirements.txt
playwright install chromium

uvicorn app.main:app --reload
```
Set `MOCK_MODE=true` to run the full pipeline offline with deterministic mock pages. For real collection set it to `false`; if Chromium is unavailable the pipeline can fall back to static HTTP extraction (clearly marked in the report).

When MongoDB is unavailable and `IN_MEMORY_PERSISTENCE=true` (the mock-mode default), analyses and incremental tracking state are kept in process memory so the dashboard and repeat-run change detection remain usable; everything resets when the server restarts. Set it to `false` outside local demos to require MongoDB.

Run the pipeline directly:
```bash
python orchestrator.py
```

2. Frontend (Next.js)
```bash
cp client/.env.example client/.env.local  # NEXT_PUBLIC_API_URL=http://localhost:8000
cd client
npm install
npm run dev
```
The frontend will be available at http://localhost:3000 and the backend API at http://localhost:8000. The dashboard calls the API directly from the browser, so keep the backend CORS origins aligned with the frontend URL (the defaults allow `localhost:3000` and `127.0.0.1:3000`).

## 🧪 Tests
```bash
python -m pytest tests/ -q
```
The offline suite uses mock pages and in-memory tracking storage; no browser binaries, network, MongoDB, or Gemini credentials are required.
