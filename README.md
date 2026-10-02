# CompetitorIQ

> Autonomous AI competitive intelligence engine for startup founders, product strategists, and venture operators.

CompetitorIQ takes a target company name and produces an in-depth, citation-grounded competitive intelligence report. It uses a multi-agent LangGraph supervisor pipeline equipped with Tavily web search, real-time Server-Sent Events (SSE) streaming, and dual human-in-the-loop checkpoints.

---

## Architecture & System Overview

- **Backend**: Python 3.11+, FastAPI, LangGraph, LangChain, Anthropic Claude 3.5 Sonnet, Tavily Search API.
- **Frontend**: Next.js 15 (App Router), TypeScript, Tailwind CSS, Lucide Icons, React Markdown.
- **Checkpointer**: Persistent SQLite with Write-Ahead Logging (`WAL` mode) and busy timeouts.
- **Protocol**: Filtered, type-safe Server-Sent Events (`text/event-stream`).

### Pipeline Stages & Checkpoints
1. **Planner Agent**: Decomposes target company into 3–4 non-overlapping research tasks across business domains (Pricing, Features, Customer Sentiment, News & Funding).
2. **Checkpoint 1 (Plan Review)**: Human-in-the-loop interrupt. User can review proposed tasks, remove unwanted tasks, or approve.
3. **Parallel Research Workers (`Send` API)**: Dynamically dispatches concurrent search workers via Tavily. Web evidence is extracted and scored with deterministic confidence metrics.
4. **Writer Agent**: Merges findings via `operator.add` reducer, grounds every claim with inline citations `[X]`, and synthesizes a preliminary Markdown draft.
5. **Checkpoint 2 (Draft Review)**: Human-in-the-loop interrupt. User reviews formatted Markdown draft and can either approve or request targeted revisions in a revision loop.
6. **Publication**: Emits finalized executive report with Markdown download and clipboard copy affordances.

---

## Important Architectural Note: Ephemeral SQLite on Render

> [!NOTE]
> **Deliberate Scoping Decision for Portfolio Demo**
> In this deployment, the backend checkpointer uses **SQLite (`checkpoints.db`) with WAL mode** running on Render's local disk.
> 
> - **The Ephemeral Disk Characteristic**: Render's free and starter web services utilize ephemeral filesystems. When the service spins down from inactivity, restarts, or redeploys, the local disk is refreshed.
> - **Cold-Start Resilience**: The application is architected to never crash on startup if `checkpoints.db` is missing; `get_sqlite_checkpointer()` automatically creates a fresh database schema (`checkpoints`, `writes`) on cold start.
> - **Single-Instance Suitability**: For a portfolio demo (single server instance, 1–2 concurrent users), SQLite + WAL mode provides lightweight persistence and zero infrastructure overhead.
> - **Production Scale Path**: In a commercial multi-instance production environment where containers scale across multiple hosts, SQLite cannot synchronize across disparate disks. The production evolution is to swap `CompetitorIQSqliteSaver` for LangGraph's native `PostgresSaver` backed by a managed PostgreSQL cluster (e.g. Supabase, Neon, or Railway Postgres).

---

## Deployment Architecture

### 1. Backend on Render
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port $PORT`
- **Environment Variables**:
  - `ANTHROPIC_API_KEY`: Anthropic API secret key
  - `TAVILY_API_KEY`: Tavily web search API secret key
  - `ALLOWED_ORIGINS`: Comma-separated allowed frontend domains (e.g. `https://competitor-iq.vercel.app`)

### 2. Frontend on Vercel
- **Framework Preset**: Next.js
- **Root Directory**: `frontend`
- **Build Command**: `next build`
- **Environment Variables**:
  - `NEXT_PUBLIC_API_URL`: Render backend URL (e.g. `https://competitor-iq-backend.onrender.com`)

---

## Local Development Quickstart

### Prerequisites
- Python 3.11+
- Node.js 18+

### Backend Setup
```bash
python -m venv .venv
# On Windows: .venv\Scripts\activate | On macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env # Add your ANTHROPIC_API_KEY and TAVILY_API_KEY
uvicorn app.main:app --app-dir backend --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev
# Open http://localhost:3000
```
