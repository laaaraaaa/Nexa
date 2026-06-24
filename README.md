Nexa
Nexa is an autonomous CI/CD healing agent. When a GitHub Actions pipeline fails, Nexa fetches the failure logs, reasons about the root cause using a memory of past failures, and — when confident enough — opens a pull request with a fix. Every outcome feeds back into memory, so the system gets more accurate over time.
This is not a LangChain wrapper or a chatbot. The memory system, vector search, and agent loop are built from scratch.

How it works
A push to your repository triggers a GitHub Actions workflow. If it fails, GitHub fires a webhook to Nexa's FastAPI server. From there:

Nexa fetches the real failure logs via the GitHub API
It converts the error message into a 384-dimensional vector embedding
It searches episodic memory for semantically similar past failures using cosine similarity
It sends the failure details and memory context to an LLM (Llama 3.3 70B via Groq)
The LLM returns an error classification, root cause, suggested fix, and confidence rating
If confidence is HIGH and the fix pattern is recognized, Nexa creates a branch, commits the fix, and opens a pull request autonomously
When CI runs on the fix PR, Nexa's validator checks the result and updates memory accordingly

The system only acts autonomously on high-confidence scenarios. Lower confidence results are stored in memory and surfaced for human review.

Memory architecture
Nexa uses a three-layer memory system:
Episodic memory stores every CI failure event, fix attempt, and outcome in PostgreSQL. This is the raw history the system reasons over.
Semantic memory is powered by pgvector. Each error message is embedded using sentence-transformers (all-MiniLM-L6-v2) and stored as a 384-dimensional vector. Similarity search uses cosine distance, so Nexa can find related past failures even when the error messages are worded differently.
Working memory uses Redis with TTL-based expiration to track active runs and open fix PRs. This prevents duplicate processing when GitHub fires multiple webhook events for the same failure.

Stack
LayerTechnologyBackendPython, FastAPIDatabasePostgreSQL + pgvectorWorking memoryRedisEmbeddingssentence-transformers (all-MiniLM-L6-v2)LLMLlama 3.3 70B via Groq APIGitHub integrationPyGithubDashboardNext.js, Tailwind CSSTunnel (dev)Cloudflare Tunnel

Project structure
nexa/
├── app/
│   ├── agent/
│   │   ├── orchestrator.py     # core agent loop — analyze, decide, act
│   │   └── validator.py        # checks PR CI status, updates memory
│   ├── memory/
│   │   ├── models.py           # episodic memory schema
│   │   ├── database.py         # async postgres connection
│   │   ├── operations.py       # store, search, retrieve memories
│   │   ├── embeddings.py       # sentence-transformer wrapper
│   │   └── working_memory.py   # redis short-term memory
│   ├── tools/
│   │   └── github_client.py    # GitHub API — logs, branches, PRs
│   ├── api/
│   │   └── dashboard.py        # REST endpoints for the dashboard
│   └── main.py                 # FastAPI app, webhook handlers
├── dashboard/                  # Next.js memory explorer
├── DECISIONS.md                # architectural decision log
└── requirements.txt

Running locally
Prerequisites: Python 3.11+, Node.js 18+, PostgreSQL 18 with pgvector, Redis
1. Clone and install dependencies
bashgit clone https://github.com/laaaraaaa/Nexa.git
cd Nexa
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
2. Set up environment variables
Create a .env file in the project root:
GITHUB_WEBHOOK_SECRET=your_webhook_secret
DATABASE_URL=postgresql+asyncpg://postgres:your_password@127.0.0.1:5432/nexa
GROQ_API_KEY=your_groq_api_key
GITHUB_TOKEN=your_github_personal_access_token
3. Set up the database
bashpsql -U postgres -c "CREATE DATABASE nexa;"
psql -U postgres -d nexa -c "CREATE EXTENSION IF NOT EXISTS vector;"
python -m app.memory.init_db
4. Start the server
bashuvicorn app.main:app --reload --port 8000
5. Expose locally with Cloudflare Tunnel
bashcloudflared tunnel --url http://localhost:8000
Register the generated URL as a webhook in your GitHub repo settings (Settings > Webhooks). Subscribe to workflow_run and check_run events.
6. Start the dashboard
bashcd dashboard
npm install
npm run dev
Visit http://localhost:3000 to see the memory explorer.

Key design decisions
See DECISIONS.md for the full architectural decision log. A few highlights:
PostgreSQL over a dedicated vector database — the project needs relational storage for structured failure data anyway. Adding pgvector keeps everything in one place without introducing a second database service.
HIGH confidence gating — Nexa only acts autonomously when the LLM assigns HIGH confidence. An incorrect autonomous fix on top of an existing failure makes things worse. Lower confidence scenarios are stored in memory for human review.
Custom memory layers over LangChain memory — building the memory system from scratch gives full control over how memories are stored, searched, and used as context. It also means the system can be reasoned about and debugged without understanding a framework's abstractions.
UUIDs as primary keys — avoids leaking record counts and works correctly in distributed contexts.

Dashboard
The Next.js dashboard at localhost:3000 shows a live view of Nexa's memory — every failure Nexa has seen, what fix it attempted, whether it opened a PR, and whether that PR's CI passed. It polls the backend every 10 seconds.

Groq API
Nexa uses Groq's inference API to run Llama 3.3 70B. Groq offers a free tier with generous rate limits, which is sufficient for development and demonstration. Sign up at console.groq.com.
