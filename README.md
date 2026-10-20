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
