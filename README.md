🚀 Nexus Intel
Autonomous B2B Market & Competitor Intelligence Platform

Built for KriticalHacks 2026 by Team Mutex Cartel

Great innovations often exist, but tracking the competition manually takes away from building them. Nexus Intel is a unified digital platform that empowers B2B SaaS founders, product managers, and venture capitalists to discover, evaluate, and track competitor pricing and feature updates through an autonomous AI-driven workflow. From navigating complex websites to synthesizing structured data, we reduce hours of manual research down to just 30 seconds.

Problem Statement
Businesses struggle to efficiently track competitor pricing changes, stealth feature launches, and hidden site updates manually.

Dynamic Web Barriers: Traditional scrapers fail on interactive elements like pricing toggles, JavaScript pop-ups, and hidden accordion menus.

State Loss: Standard tools reset session states, making it impossible to capture modified web DOMs after navigating a multi-step user flow.

Data Overload: Raw scraped markdown or HTML is unstructured and time-consuming to parse into actionable business insights.

Core Challenge: How can we create an autonomous, transparent system that moves from Search → Navigate → Extract → Synthesize → Report without human intervention?

💡 Our Solution
Nexus Intel provides an end-to-end, outcome-driven competitor intelligence workflow:

Competitor Discovery → Autonomous Navigation (TinyFish) → Stateful DOM Extraction

→ AI Synthesis & Structuring (Gemini 1.5) → Live Dashboard Tracking

✨ Key Features
🎯 Autonomous DOM Navigation — Interacts with complex web pages (e.g., clicking "Annual Billing", expanding accordions) without human intervention.

🔄 Stateful Session Tracking — Preserves browser states (session_id) between agent actions and data fetching to ensure accurate DOM capture.

🤖 Structured AI Synthesis — Passes raw markdown into Gemini 1.5 Flash with strict Pydantic schemas to output clean, reliable JSON data.

👁️ Transparency & Alerts — Live Next.js dashboard for real-time tracking, historical price comparisons, and immediate feature alerts.

🔐 Serverless Scalability — Built to operate with zero idle server costs, utilizing highly efficient, asynchronous pipeline execution.
Architecture
┌──────────────────────────────────────────────────────────┐
│          B2B Founders · Product Managers · VCs           │
└──────────────────────────────────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│            Next.js Frontend (Web Dashboard)              │
└──────────────────────────┬───────────────────────────────┘
                           │  REST APIs
┌──────────────────────────▼───────────────────────────────┐
│         FastAPI Backend (Asynchronous Pipeline)          │
└───────────────┬──────────────────────────┬───────────────┘
                │                          │
┌───────────────▼──────────┐   ┌───────────▼───────────────┐
│   MongoDB Database       │   │ TinyFish Web Agents &     │
│   (State & JSON Data)    │   │ Gemini 1.5 Flash LLM      │
└──────────────────────────┘   └───────────────────────────┘
🛠️ Tech Stack
Layer                      Technology
Frontend               Next.js, TailwindCSS
Backend                  Python,FastAPI
Database                  MongoDB Atlas
Web Agents        TinyFish API (Search, Agent Navigation, Fetch)
AI/Synthesis           Google Gemini 1.5 Flash
⚙️ Quick Setup
Prerequisites

Python 3.10+

Node.js (v18+)

MongoDB Atlas Account

Git

1. Clone the repository
git clone https://github.com/Lakshaycodes-dev/Nexus-Intel.git
cd Nexus-Intel
2. Install Backend Dependencies
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
3. Configure Environment Variables
Create a .env file in the root directory:
TINYFISH_API_KEY=your_tinyfish_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
MONGODB_URI=mongodb://localhost:27017
MOCK_MODE=true
4. Run Locally
# Start backend orchestrator
python orchestrator.py
👨‍💻 Team Mutex Cartel
Member                              Responsibility                 
Lakshay                   Team Lead, Pipeline Orchestration & Integration
Riyanshu                  Core Developer (TinyFish Web Agent Navigation)
Navya Jaiswal                            Core Developer
Yashavi                                  Core Developer
Jatin Sharma                             Core Developer
🌍 Impact & Benefits
For Startups: Faster discovery of competitor pricing shifts, reducing research time by 480x.

For VCs: Evidence-based market mapping and due diligence at the click of a button.

Economic: Sustainable SaaS model with ~88% gross margins leveraging serverless AI execution.
