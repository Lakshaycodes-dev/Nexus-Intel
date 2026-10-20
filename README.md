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

Bash
git clone https://github.com/Lakshaycodes-dev/Nexus-Intel.git
cd Nexus-Intel
2. Set up a Virtual Environment

Bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
3. Install Dependencies

Bash
pip install -r requirements.txt
4. Configure Environment Variables
Create a .env file in the root directory. Never commit this file.

Code snippet
TINYFISH_API_KEY=your_tinyfish_api_key
GEMINI_API_KEY=your_gemini_api_key
MONGO_URI=your_mongodb_connection_string
5. Run the Orchestrator Pipeline

Bash
python orchestrator.py
Note: The project includes a MOCK_MODE in config.py for safe testing without consuming API credits.

📂 Project Structure
Plaintext
📦 Nexus-Intel
 ┣ 📂 services/
 ┃ ┣ 📜 tinyfish_search.py     # Discovers competitor URLs
 ┃ ┣ 📜 tinyfish_agent.py      # Navigates DOM & captures session_id
 ┃ ┣ 📜 tinyfish_fetch.py      # Extracts Markdown using active session_id
 ┃ ┗ 📜 gemini_service.py      # Structures data into JSON schemas
 ┣ 📂 utils/
 ┃ ┗ 📜 navigation_helpers.py  # Retry logic and guardrails for the agent
 ┣ 📂 output/                  # Stores generated markdown and JSON reports
 ┣ 📜 orchestrator.py          # Main execution pipeline tying modules together
 ┣ 📜 config.py                # Global settings and MOCK_MODE toggles
 ┣ 📜 requirements.txt         # Python dependencies
 ┗ 📜 .env.example             # Template for API keys
💼 Business & Revenue Model
Nexus Intel is designed as a highly scalable B2B SaaS with ~85% to 90% gross margins due to our low-cost, serverless AI execution pipeline (~$0.10 per deep run).

Starter ($49/month): Up to 5 competitors, weekly updates, core tracking.

Growth ($149/month): Up to 25 competitors, full TinyFish UI interaction (pricing toggles), real-time alerts.

Enterprise ($499+/month): Unlimited tracking, custom Gemini JSON schemas, Slack/CRM webhook integration.

👥 The Team (Mutex Cartel)
Lakshay – Team Lead & Pipeline Orchestration

Riyanshu – Core Developer

Yashavi Singh – Core Developer

Jatin Sharma – Core Developer

Navya Jaiswal – Core Developer
