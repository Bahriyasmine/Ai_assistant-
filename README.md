# CSO Intelligence Assistant

> A production-grade AI assistant for a Chief Strategy Officer at an international financial center — built with **FastAPI**, **OpenAI Responses API**, and a real-time streaming UI.

---

## Overview

This project is a secure, RAG-powered intelligence assistant designed for executive decision-making. It transforms a 24-document strategic knowledge base into an interactive intelligence platform with three distinct modes:

| Mode | What it does |
|------|-------------|
| **Strategic Chat** | Ask any question, get a streamed, cited answer grounded in the knowledge base |
| **Daily Digest** | One-click summary of the 6 most critical intelligence signals of the day |
| **Board Brief** | Auto-generates a structured executive brief with actions at 7 / 30 / 90 days |

---

## Demo

**Chat** — streaming responses with source citations, full conversation memory

**Daily Digest** — 6 intelligence cards covering markets, competitors, regulation, performance, risk, and opportunities

**Board Brief** — formal executive document with strategic implications and recommended actions

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | **FastAPI** (async, Python 3.11) |
| AI / RAG | **OpenAI Responses API** + `file_search` tool (managed vector store) |
| Streaming | Server-Sent Events (SSE) via `client.responses.stream()` |
| Frontend | Vanilla HTML/CSS/JS — no build step, no framework, no dependencies |
| Auth | API key via `X-API-Key` header (FastAPI Security dependency) |
| Config | Pydantic Settings (`.env`) + YAML (`core/config.yaml`) |
| Containerization | Docker (python:3.11-slim) |

---

## Architecture

```
assistant_v2/
├── main.py                          # FastAPI app — mounts API + serves UI
├── Dockerfile
├── requirements.txt
├── .env.example                     # copy to .env and fill in secrets
│
├── core/
│   ├── config.yaml                  # AI instructions (chat, digest, board brief)
│   ├── config.py                    # Pydantic settings — loads .env + YAML
│   ├── client.py                    # AsyncOpenAI singleton
│   ├── security.py                  # API key auth dependency
│   ├── exceptions.py                # domain exceptions → HTTP status codes
│   └── logging.py                   # structured logging
│
├── models/
│   └── schemas.py                   # Pydantic request/response models
│
├── services/
│   ├── openai_service.py            # Responses API: chat, stream, digest, brief
│   └── vector_store.py              # vector store lifecycle (create, upload, delete)
│
├── api/
│   ├── chat.py                      # POST /chat  /chat/stream  /board-brief  /summarize
│   ├── vector_store.py              # GET|POST|DELETE /vector-store + /files
│   └── routes.py                    # combines routers
│
├── data/
│   └── cso_intelligence_knowledge_base.txt   # 24 strategic intelligence documents
│
└── static/
    └── index.html                   # 3-tab UI (Chat / Daily Digest / Board Brief)
```

---

## Key Design Decisions

### Managed RAG via OpenAI file_search
Rather than building a custom embedding pipeline, the project leverages OpenAI's **Responses API** with the `file_search` tool. OpenAI handles chunking, embedding, indexing, and semantic retrieval against the vector store — zero infrastructure to maintain.

### Server-side conversation memory
Each API response returns a `response_id`. Passing it back as `previous_response_id` continues the conversation without sending history from the client — OpenAI holds the full context server-side. This means multi-turn conversation is nearly free in terms of payload size.

### SSE streaming
`POST /chat/stream` opens a Server-Sent Events channel. The backend iterates over `response.output_text.delta` events and forwards each token to the browser in real time — same pattern used by ChatGPT.

### Single-file knowledge base
The 24 source documents are combined into one knowledge base file. This is intentional: it simplifies ingestion and keeps the vector store to a single managed file.

### Zero-JS-framework frontend
The entire UI is one `index.html` file. No build step, no npm, no bundler. The recruiter can open it immediately. Markdown rendering is done with a lightweight inline parser.

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/Bahriyasmine/Ai_assistant-
cd Ai_assistant-
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
OPENAI_API_KEY=sk-...           # required
OPENAI_MODEL=gpt-4o             # optional, default gpt-4o
API_KEY=your-secret-key         # optional — leave empty to disable auth
```

### 3. Run

```bash
uvicorn main:app --reload --port 8000
```

| URL | Purpose |
|-----|---------|
| `http://localhost:8000` | Intelligence UI |
| `http://localhost:8000/docs` | Interactive API explorer (Swagger) |

### 4. Initialize the knowledge base (first run only)

```bash
# Create vector store and upload knowledge base
curl -X POST http://localhost:8000/vector-store \
     -H "X-API-Key: your-secret-key"

# Confirm it's ready
curl http://localhost:8000/vector-store/status \
     -H "X-API-Key: your-secret-key"
```

The vector store ID is automatically saved to `.env` — subsequent restarts pick it up with no manual step.

---

## Docker

```bash
# Build
docker build -t cso-assistant .

# Run
docker run -p 8000:80 \
  -e OPENAI_API_KEY=sk-... \
  -e API_KEY=your-secret-key \
  -e VECTOR_STORE_ID=vs_... \
  cso-assistant
```

---

## API Reference

### Chat

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/chat` | Full JSON response (non-streaming) |
| `POST` | `/chat/stream` | SSE streaming — tokens arrive in real time |
| `POST` | `/chat/board-brief` | Structured executive board brief |
| `POST` | `/chat/summarize` | Daily intelligence digest |

**Example — streaming chat:**

```bash
curl -X POST http://localhost:8000/chat/stream \
     -H "Content-Type: application/json" \
     -H "X-API-Key: your-secret-key" \
     -d '{"question": "Where is global capital moving?"}'
```

**Conversation chaining:**

```json
{
  "question": "What are the implications for us?",
  "previous_response_id": "resp_abc123"
}
```

### Vector Store

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/vector-store/status` | Check readiness |
| `POST` | `/vector-store` | Create store + auto-upload `data/` files |
| `DELETE` | `/vector-store` | Delete the configured store |
| `GET` | `/vector-store/files` | List indexed files |
| `POST` | `/vector-store/files` | Upload a file |
| `DELETE` | `/vector-store/files/{file_id}` | Remove a file |

### Other

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/health` | Liveness probe |
| `GET` | `/` | Serves the UI |

---

## Knowledge Base

`data/cso_intelligence_knowledge_base.txt` contains 24 structured intelligence documents across 6 categories:

| Category | Documents | Coverage |
|----------|-----------|----------|
| Market Signals | MKT-001 → MKT-004 | Capital flows, private credit, stablecoins, fintech trends |
| Competitor Moves | COMP-001 → COMP-004 | Fast-track licensing, AI sandboxes, talent visa programs |
| Regulatory Shifts | REG-001 → REG-004 | Digital asset rules, AI governance, ESG standards |
| Internal Documents | INT-001 → INT-004 | Pipeline fund managers, deal velocity, headcount plans |
| Performance Alerts | PERF-001 → PERF-004 | Fund domiciliation, digital asset licensing, ESG programmes |
| Risk Indicators | RISK-001 → RISK-004 | Regulatory lag, talent gaps, service level breaches |

---

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | Yes | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o` | Model ID |
| `VECTOR_STORE_ID` | No | — | Pre-existing vector store (skips creation) |
| `DATA_DIR` | No | `data` | Directory scanned for knowledge base files |
| `API_KEY` | No | — | API key auth — empty disables auth entirely |

---

## Authentication

All `/chat` and `/vector-store` endpoints require an `X-API-Key` header when `API_KEY` is set in `.env`:

```
X-API-Key: your-secret-key
```

The UI reads this key from a hardcoded constant (`const API_KEY`) in `index.html` — replace it if you change the key.

---

## Project Context

Built as part of a technical assessment for an AI Engineer role at an international financial center. The assessment required designing a production-ready AI assistant for a Chief Strategy Officer, grounded in a proprietary strategic intelligence knowledge base.
