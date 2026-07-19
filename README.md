# Court Vision

**An NBA statistics question-answering system powered by local LLMs and semantic search.**

Ask natural-language questions about NBA games and players. Court Vision retrieves the most relevant game records using vector similarity search and passes them to a local LLM to generate grounded, data-backed answers — all running on your own machine.

---

## Motivation

Structured sports databases are rich but rigid: answering questions like *"Who led scoring in the OKC vs. LAL game on March 4?"* typically requires knowing exact column names, table joins, and precise filters. This project explores using RAG (Retrieval-Augmented Generation) to bridge that gap — turning natural-language questions into accurate answers by combining semantic search over game embeddings with LLM-generated responses.

---

## Key Features

- **Local-first** — all inference runs via [Ollama](https://ollama.com); no external API keys required
- **Semantic retrieval** — game summaries are embedded with `nomic-embed-text` and indexed using HNSW for fast cosine similarity search
- **Grounded answers** — the LLM only sees retrieved game context, reducing hallucination
- **Full-stack** — Angular chat frontend communicates with a FastAPI backend over a clean REST API
- **Self-contained** — includes two full NBA seasons of game and player data (2023–24 and 2024–25)
- **Dockerized** — one `docker compose up` starts PostgreSQL, Ollama, and the API server

---

## System Architecture

```
┌─────────────────── DATA PIPELINE (one-time setup) ────────────────────┐
│                                                                         │
│  CSV Files ──► ingest.py ──────────────────────► PostgreSQL/pgvector   │
│  · game_details                                   · 4 tables loaded     │
│  · player_box_scores       embed.py               · ~1,682 games        │
│  · players            ◄── reads game_details      · ~36,200 box scores  │
│  · teams                        │                                       │
│                                 ▼                                       │
│                       Ollama (nomic-embed-text)                         │
│                                 │                                       │
│                       768-dim embeddings stored                         │
│                       in game_details.embedding                         │
│                       HNSW index for fast ANN search                    │
└─────────────────────────────────────────────────────────────────────────┘

┌──────────────────────── QUERY FLOW (runtime) ──────────────────────────┐
│                                                                         │
│  Angular         FastAPI            PostgreSQL         Ollama           │
│  Frontend        server.py          + pgvector                          │
│     │                │                   │                │             │
│     │─ POST /chat ──►│                   │                │             │
│     │                │─ embed question ─────────────────►│             │
│     │                │◄─ 768-dim vector ─────────────────│             │
│     │                │─ cosine search ──►│                │             │
│     │                │◄─ top-5 rows ────│                │             │
│     │                │─ build context    │                │             │
│     │                │─ generate ───────────────────────►│             │
│     │                │◄─ answer text ────────────────────│             │
│     │◄─ JSON ────────│                   │                │             │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Technology Stack

| Component | Technology |
|---|---|
| Database | PostgreSQL 16 + pgvector |
| Embedding model | nomic-embed-text (via Ollama) |
| Language model | llama3.2:3b (via Ollama) |
| Backend API | FastAPI + SQLAlchemy + Pydantic |
| Frontend | Angular 15 |
| Infrastructure | Docker Compose |
| Data | ~38,000 rows across 4 CSV tables |

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose
- [Ollama](https://ollama.com) (or use the Ollama container — see below)
- Node.js 18+ and Angular CLI 15 (for frontend development only)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/your-username/court-vision.git
cd court-vision
```

### 2. Start infrastructure

```bash
docker compose up -d db ollama
```

This starts:
- PostgreSQL 16 with pgvector on port `5432`
- Ollama on port `11434`

### 3. Pull Ollama models

The embedding and LLM models must be pulled before the pipeline can run. With the Ollama container running:

```bash
docker exec ollama ollama pull nomic-embed-text
docker exec ollama ollama pull llama3.2:3b
```

This is a one-time step. Models are stored in the `ollamavol` Docker volume and persist across restarts.

### 4. Run the data pipeline

Ingest the CSV data into PostgreSQL, then generate and store embeddings:

```bash
# Load the four CSV tables into PostgreSQL
docker compose run --rm app python -m backend.ingest

# Generate embeddings for all game records and build the HNSW index
docker compose run --rm app python -m backend.embed
```

Embedding ~1,682 game records takes a few minutes depending on hardware.

### 5. Start the API server

```bash
docker compose up app
```

The FastAPI server is now available at `http://localhost:8000`.

---

## Environment Variables

Copy `.env.example` to `.env` to override defaults when running outside Docker:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `DB_DSN` | `postgresql://nba:nba@localhost:5432/nba` | PostgreSQL connection string |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama base URL |
| `EMBED_MODEL` | `nomic-embed-text` | Embedding model name |
| `LLM_MODEL` | `llama3.2:3b` | LLM name for answer generation |

---

## Running the Frontend

```bash
cd frontend
npm install
npm start
```

The Angular dev server starts at `http://localhost:4200`. It proxies chat requests to the FastAPI backend at `http://localhost:8000`.

---

## Usage

With all services running, open `http://localhost:4200` in your browser. Type a question into the chat box and press **Send**.

### Example questions

```
How many points did the Warriors score against Sacramento on October 27, 2023?

Who won the 2023 Christmas Day game between Golden State and Denver?

Who was the leading scorer in OKC's 144-110 win over Sacramento on February 1, 2024?

How many points did Victor Wembanyama score in his NBA debut?

Which player recorded a triple-double in Denver's 132-121 win over Utah on December 30, 2024?
```

---

## Batch RAG Runner

`backend/rag.py` can be used to run the RAG pipeline over a file of questions and write structured JSON output:

```bash
python -m backend.rag \
  --questions path/to/questions.json \
  --template  path/to/answer_template.json \
  --output    path/to/answers.json \
  --k 5
```

**`questions.json` format:**
```json
[
  { "id": 1, "question": "How many points did LeBron score on January 16, 2023?" }
]
```

**`answer_template.json` format:**
```json
[
  { "id": 1, "result": { "player_name": "", "points": 0, "evidence": [{ "table": "player_box_score", "id": 0 }] } }
]
```

---

## Data Pipeline Details

### Ingestion (`backend/ingest.py`)

Loads four CSV files from `backend/data/` into PostgreSQL using pandas and SQLAlchemy. Tables are replaced on each run. Also ensures the `pgvector` extension is installed.

### Embedding generation (`backend/embed.py`)

For each game in `game_details`, constructs a short human-readable summary:

```
Season: 2024
Date: 2025-01-15
(112) Oklahoma City Thunder W vs Los Angeles Lakers L (108)
```

Each summary is embedded via `nomic-embed-text` and stored as a `vector(768)` column. An HNSW index (cosine distance) is built for fast approximate nearest-neighbour search.

---

## Repository Structure

```
court-vision/
├── backend/
│   ├── config.py            # environment variable configuration
│   ├── utils.py             # Ollama HTTP client wrappers
│   ├── ingest.py            # CSV → PostgreSQL loader
│   ├── embed.py             # embedding generation + HNSW index
│   ├── rag.py               # batch Q&A pipeline (CLI)
│   ├── server.py            # FastAPI endpoint
│   └── data/
│       ├── game_details.csv       # ~1,682 games, 2023–24 and 2024–25
│       ├── player_box_scores.csv  # ~36,200 player game lines
│       ├── players.csv            # ~451 players
│       └── teams.csv              # 30 teams
├── frontend/
│   └── src/app/
│       ├── app.component.*        # chat UI
│       └── services/
│           ├── base.service.ts    # HTTP base class
│           └── chat.service.ts    # /api/chat client
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## Known Limitations

- **Game-level retrieval only** — embeddings are built on `game_details` rows. Questions about individual player stats are answered by the LLM inferring from game context, not by directly retrieving `player_box_scores`. This limits accuracy for player-level queries.
- **Small LLM** — `llama3.2:3b` is chosen for speed and low hardware requirements. Answer quality improves noticeably with larger models (e.g. `llama3.2:8b`).
- **No streaming** — responses are returned in a single HTTP response; there is no token streaming to the frontend.
- **No conversation history** — each question is answered independently; the system has no memory of prior turns.
- **English only** — prompts and data are in English.

---

## Future Improvements

- **Multi-table retrieval** — embed and index `player_box_scores` to enable accurate player-level Q&A
- **Hybrid search** — combine keyword (BM25) and vector search for better recall on exact names and dates
- **Streaming responses** — use FastAPI's `StreamingResponse` with Ollama's streaming API
- **Conversation context** — maintain a sliding window of prior turns in the prompt
- **Larger model support** — make the model configurable in the UI; allow hot-swapping between available Ollama models
- **Season filter** — allow users to restrict queries to a specific season
