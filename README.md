# 🌐 Nexus Intel
**AI-Powered B2B Market Intelligence Platform**

Nexus Intel is a full-stack platform designed for B2B Founders, Product Managers, and VCs to extract, synthesize, and act upon market data. Built by **Team Mutex Cartel** for KriticalHacks 2026, it utilizes a network of AI web agents to automate intelligence gathering with zero idle server costs.

## ✨ Key Features
* **Agentic Web Scraping:** TinyFish Web Agents autonomously navigate, search, and fetch unstructured data from the web.
* **LLM Synthesis:** Google Gemini 1.5 Flash processes raw HTML/JSON into actionable market intelligence.
* **Asynchronous Pipeline:** FastAPI backend ensures high-throughput, non-blocking data orchestration.
* **Serverless Scalability:** Built for zero idle server costs with an efficient REST API architecture.
* **Modern Dashboard:** Next.js and TailwindCSS provide a responsive, real-time web interface.

## 🏗️ Architecture & Tech Stack
* **Frontend:** Next.js, TailwindCSS, React
* **Backend:** Python, FastAPI
* **Database:** MongoDB Atlas (State & JSON Data)
* **AI & Agents:** TinyFish Web Agents API, Google Gemini 1.5 Flash

## 📂 Monorepo Structure
This repository uses a monorepo architecture, strictly separating the Next.js client from the Python orchestrator to prevent routing conflicts.
```text
Nexus-Intel/
├── client/                 # Next.js Frontend Environment
│   ├── app/                # Web dashboard and UI routing
│   ├── components/         # Reusable React components
│   ├── .env.local          # Frontend secrets (git-ignored)
│   └── package.json        
├── app/                    # FastAPI Backend Environment
│   ├── main.py             # Asynchronous pipeline orchestrator
│   └── utils/              # Shared Python utilities
├── .env                    # Backend secrets (git-ignored)
├── requirements.txt        
└── README.md
Environment Variables
1. Backend (/.env)
GEMINI_API_KEY=your_google_gemini_key
TINYFISH_API_KEY=your_tinyfish_key
MONGODB_URI=your_mongodb_connection_string
2. Frontend (/client/.env.local)
NEXT_PUBLIC_API_URL=http://localhost:8000
🚀 Quick Setup
1. Backend Installation (FastAPI)
Open a terminal in the root directory:
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Start the asynchronous pipeline
uvicorn app.main:app --reload
2. Frontend Installation (Next.js)
Open a second terminal and navigate to the isolated frontend folder:
cd client

# Install dependencies
npm install

# Start the web dashboard
npm run dev
The frontend will be available at http://localhost:3000 and the backend API at http://localhost:8000.
