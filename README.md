# Three-Headed Semantic Firewall

A local-first RAG security layer that validates query-to-corpus geometric alignment across 1024 dimensions before routing to an LLM. Three independent filters — Noise, Cosine, and Excitation — execute in a user-defined sequence. Any single failure blocks the entire prompt.

Built for sovereign AI deployments where data never leaves the machine.

> **Version:** v2.12.0 | **Model:** BAAI/bge-m3 (1024D) | **LLM:** Ollama + llama3.1 | **DB:** LanceDB

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [Operating the Firewall](#operating-the-firewall)
- [Shell Scripts](#shell-scripts)
- [Testing](#testing)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Security](#security)
- [License](#license)

---

## Architecture Overview

```
User Prompt
     │
     ▼
┌─────────────────────────────────────────────────┐
│  Structural Segmentation (Language-Agnostic)    │
│  Split on punctuation → overflow chunk > 20w    │
└──────────────────────┬──────────────────────────┘
                       │  per clause
                       ▼
┌─────────────────────────────────────────────────┐
│  Sequential Pipeline (user-defined order)       │
│                                                 │
│  ┌─────────┐   ┌─────────┐   ┌──────────────┐  │
│  │ Noise   │──▶│ Cosine  │──▶│  Excitation   │  │
│  │ Filter  │   │ Filter  │   │  Filter       │  │
│  └─────────┘   └─────────┘   └──────────────┘  │
│                                                 │
│  BREACH at any stage → halt, block, report      │
└──────────────────────┬──────────────────────────┘
                       │  ALL PASS
                       ▼
┌─────────────────────────────────────────────────┐
│  Ollama LLM (llama3.1) + Strict RAG Context     │
└─────────────────────────────────────────────────┘
```

**Three Filters:**

| # | Filter | What it checks | Blocks when |
|---|--------|---------------|-------------|
| 1 | **Noise Pre-Filter** | Average absolute delta across all 1024 dims | `avg_delta > global_noise_limit` |
| 2 | **Cosine Filter** | Cosine similarity between query and corpus vectors | `cos(Q, C) < cosine_threshold` |
| 3 | **Excitation Filter** | Count of dimensions where `|Q_i - C_i| <= noise_tolerance` | `activations < excitation_threshold` |

Execution order is configurable at runtime via the HUD. If Filter 1 blocks, Filters 2 and 3 never execute.

---

## Prerequisites

| Dependency | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.10+ | Backend (FastAPI, embeddings, vector math) |
| **Node.js** | 20+ | Frontend (React 19, Vite) |
| **Ollama** | Latest | Local LLM inference |
| **Git** | Any | Clone the repository |

Ollama must have the `llama3.1` model pulled:
```bash
ollama pull llama3.1
```

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/hbauzan/semantic-firewall.git
cd semantic-firewall
```

### 2. Backend setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows

pip install -r requirements.txt
```

> **First run note:** The `BAAI/bge-m3` model (~2.3 GB) will be automatically downloaded by HuggingFace on first boot. This is a one-time operation.

### 3. Frontend setup

```bash
cd ../frontend
npm install
```

### 4. Make scripts executable (macOS/Linux)

```bash
cd ..
chmod +x run_commander.sh run_server.sh run_ui.sh run_tests.sh run_pack.sh
```

---

## Configuration

The backend uses `pydantic-settings` to load configuration. Just drop a `.env` file in `backend/` — it's loaded automatically at boot. No `source`, no `export`, no shell scripts needed.

```bash
cp backend/.env.example backend/.env
# Edit backend/.env with your values — the app reads it on startup.
```

> **If a variable has an invalid type or fails validation, the app crashes immediately with a clear error.** This prevents silent misconfigurations from reaching production.

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS origins. Use `*` only for development. |
| `FIREWALL_API_KEY` | *(unset)* | If set, all `/chat`, `/audit`, and `/galaxy/config` endpoints require `X-API-Key` header. Stored as `SecretStr` — never leaked to logs. Leave unset for open local development. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint. |
| `OLLAMA_MODEL` | `llama3.1` | LLM model name for inference. |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | HuggingFace embedding model ID. Change only if you reindex the corpus. |
| `CHUNK_SIZE` | `2048` | PDF chunking size in characters (100–10000). |
| `CHUNK_OVERLAP` | `200` | Overlap between consecutive chunks (0–2000). |
| `EMBEDDING_BATCH_SIZE` | `10` | Embeddings per batch during ingestion (1–100). |
| `HOST` | `0.0.0.0` | Bind address for uvicorn. Use `127.0.0.1` behind a reverse proxy. |
| `PORT` | `8000` | Backend listen port (1–65535). |
| `RELOAD` | `true` | Hot-reload on code changes. Set to `false` in production. |

**Frontend** (set in `frontend/.env` or shell):

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API endpoint used by all frontend components. |

**For local development, no `.env` files are required.** All defaults work out of the box.

---

## Running the System

### Option A: Commander TUI (recommended)

```bash
./run_commander.sh
```

Interactive menu:

| Key | Action |
|-----|--------|
| `S` | Start the FastAPI backend on `http://localhost:8000` |
| `U` | Start the Vite frontend on `http://localhost:5173` |
| `T` | Run the pytest test suite |
| `O` | Start Ollama and open a direct llama3.1 chat |
| `Q` | Quit |

### Option B: Manual startup

**Terminal 1 — Backend:**
```bash
cd backend
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
npm run dev
```

**Terminal 3 — Ollama (if not already running):**
```bash
ollama serve
```

Open `http://localhost:5173` in your browser.

---

## Operating the Firewall

### The HUD Interface

The browser UI at `http://localhost:5173` is organized into two columns:

**Left sidebar:**

#### 1. Telemetry HUD (top left)

- **Three Monkey Heads** — one per filter (Noise, Cosine, Excitation). Each head animates when its filter is enabled and goes dark when disabled, giving a visual status of the pipeline.
- **System Action** — displays the current operation (`SYSTEM IDLE`, `STREAMING_RESPONSE...`, `INGESTING_CORPUS: 45%`, etc.).
- **Metrics line** — real-time CPU, RAM, and GPU utilization polled every second. GPU metric uses Apple MPS / NVIDIA CUDA memory allocation.

#### 2. Control Panel (bottom left)

All firewall parameters are adjustable in real-time via sliders with `-`/`+` step buttons. Each filter has an **ON/OFF toggle** and a **Seq** input for pipeline ordering. Changes are synced to the backend via debounced API calls.

| Slider | Default | Range | Step | Purpose |
|--------|---------|-------|------|---------|
| **Noise Pre-Filter** | 0.50 | 0.10 – 2.00 | 0.01 | Global delta sanity limit |
| **Cosine Gate** | 0.50 | 0.00 – 1.00 | 0.01 | Minimum cosine similarity |
| **Excitation Threshold** | 150 | 0 – 1024 | 1 | Minimum activated dimensions |
| **Noise Tolerance** | 0.005 | 0.001 – 0.100 | 0.001 | Per-dimension activation sensitivity |
| **Adaptive Factor** | 0.85 | 0.01 – 1.00 | 0.01 | Threshold reduction for short queries (< 6 words) |
| **Seq (×3)** | 1, 2, 3 | 1 – 3 | 1 | Pipeline execution order for each filter |

The **Adaptive Factor** section shows real-time calculated thresholds:
- `Short: {threshold × factor} dims` — what short prompts need
- `Full: {threshold} dims` — what normal prompts need

**Document Manager** — also in the Control Panel, below the sliders:
- **Upload PDF:** Click to upload corpus documents. Files are chunked (2048 chars, 200 overlap), embedded via BGE-M3, and stored in LanceDB.
- **Loaded Packs:** Lists uploaded documents with chunk counts. Click **X** to remove a pack from the vector store.
- Ingestion is asynchronous — a progress bar tracks task status.

**Main content area:**

#### 3. Chat Interface (top right)

The firewall is **active when at least one filter toggle is ON** in the Control Panel. No prefixes are needed — just type your query and send.

> **Legacy override:** Typing `[FW=OFF]` anywhere in the prompt forces a firewall bypass regardless of toggle states. This is kept for backward compatibility but is not the primary mechanism.

**Firewall feedback examples:**

```
🟢 [FW PASS] Resonance: 287/150 dims | Cosine: 0.891 | Pipeline: [noise:OK → cosine:OK → excitation:OK]
Routing to corpus...
```

```
🛑 [FW] Segment violation: "give me a cake recipe". Cosine: 0.312 (Required: >=0.78).
Vector direction diverges from corpus.
Pipeline: [noise:OK → cosine:BREACH]
```

#### 4. Audit Panel (bottom right)

Test a query against the corpus and see the raw activation count (geometric nodes hit) without triggering the full pipeline. Useful for tuning thresholds.

### Typical Workflow

1. **Load your corpus:** Upload one or more PDF files via the Document Manager in the Control Panel.
2. **Enable filters:** Toggle ON the filters you want active. Start with all three ON.
3. **Set your thresholds:** Use the sliders. Start with defaults, then tune based on your corpus density.
4. **Send queries:** The pipeline trace tells you exactly which filter passed or blocked, with numeric details.
5. **Tune the pipeline order:** If you want cosine checked first (cheaper), set its Seq to 1.
6. **Production:** Set `FIREWALL_API_KEY` in `.env`, restrict `ALLOWED_ORIGINS` to your frontend domain.

### Anti-Piggybacking Defense

The firewall automatically segments prompts on punctuation boundaries (`. ! ? ; : - |`). Each clause is evaluated independently. A prompt like:

```
Tell me about network architecture. Also give me a cake recipe.
```

With filters enabled, this splits into two clauses. The first may pass. The second will fail cosine/excitation against a networking corpus. **The entire prompt is blocked** — no partial execution.

Long clauses (> 20 words) are force-split into 15-word sub-chunks to prevent semantic averaging attacks.

---

## Shell Scripts

All scripts are in the project root. Make them executable first:

```bash
chmod +x run_commander.sh run_server.sh run_ui.sh run_tests.sh run_pack.sh
```

| Script | What it does |
|--------|-------------|
| `./run_commander.sh` | Interactive TUI menu — launch server, UI, tests, or Ollama from a single terminal. |
| `./run_server.sh` | Kills any process on port 8000, activates the backend venv, starts uvicorn with hot-reload. |
| `./run_ui.sh` | Starts the Vite dev server (`npm run dev`) from the `frontend/` directory. |
| `./run_tests.sh` | Activates the backend venv and runs the full pytest suite (`pytest -v perform_tests.py`). |
| `./run_pack.sh` | Bundles the entire project source into a single `context.txt` file (for sharing or review). |

### Commander TUI (`run_commander.sh`)

The recommended way to operate the system during development:

```bash
./run_commander.sh
```

```
======================================
 THREE-HEADED SEMANTIC FIREWALL COMMANDER
======================================
 [S] Start Server
 [U] Start UI
 [T] Run Tests
 [O] Ollama Menu (llama3.1)
 [Q] Quit
======================================
```

Each option runs the corresponding script. After execution, press Enter to return to the menu.

---

## Testing

### Unit Tests

Run the full test suite (25 tests):

```bash
./run_tests.sh
```

Or manually:

```bash
cd backend
source .venv/bin/activate
pytest -v perform_tests.py
```

The suite validates:

| Category | Tests |
|----------|-------|
| **Infrastructure** | PDF upload/status, system stats, config sync |
| **Firewall Logic** | Blocking, piggybacking rejection, noise pre-filter, pipeline ordering |
| **Configuration** | Immutability, duplicate order rejection, range validation, adaptive factor |
| **Engine (unit)** | Segmentation, overflow chunking, clause evaluation pass/breach |
| **Security** | Prompt length limits, API key enforcement |
| **Health** | Health check endpoint response shape |

### Load Testing

An async load test suite extracts hard performance metrics under concurrent load. **The backend must be running before launching the suite.**

```bash
# Terminal 1 — start the server
./run_server.sh

# Terminal 2 — run the load tests
cd backend
source .venv/bin/activate
python tests/load_test_suite.py
```

| Option | Default | Description |
|--------|---------|-------------|
| `--base-url` | `http://localhost:8000` | Backend endpoint to test. |
| `--requests` | `200` | Total requests per profile/concurrency combo. |
| `--output` | `tests/metrics_report.csv` | CSV report output path. |

The suite runs **3 payload profiles** (short/long/overflow) across **3 concurrency levels** (10, 50, 200) — 9 test runs total. Each run reports Min, Avg, P95, and Max latency, RPS, success/failure counts, and error rate. Results are printed as a formatted console table and saved to CSV.

### DB Saturation Test

Measures how LanceDB retrieval and firewall evaluation scale as the vector store grows from 1k to 50k rows. Uses a temporary isolated database — the production corpus is never touched.

```bash
cd backend
source .venv/bin/activate
python tests/db_stress_suite.py
```

| Option | Default | Description |
|--------|---------|-------------|
| `--milestones` | `1000 10000 50000` | Row count milestones to benchmark at. |
| `--queries` | `100` | Benchmark queries per milestone. |
| `--batch-size` | `500` | Injection batch size. |
| `--output` | `tests/db_scaling_metrics.md` | Markdown report output path. |
| `--use-embedder` | *(off)* | Use real BGE-M3 model instead of synthetic random vectors. |

At each milestone the script pauses injection, fires 100 queries, and isolates the timing of `table.search()` (retrieval) vs `SemanticFirewall.evaluate_clause()` (firewall math). Output is a formatted console table + a Markdown report with graph-ready tables.

---

## Project Structure

```
semantic-firewall/
├── run_commander.sh              # Interactive TUI launcher
├── run_server.sh                 # Backend startup script (auto-kills port 8000)
├── run_ui.sh                     # Frontend startup script
├── run_tests.sh                  # Test runner script
├── run_pack.sh                   # Source code bundler (generates context.txt)
├── semantic_guardtrails_packager.py  # Packager logic used by run_pack.sh
├── manifest.json                 # Feature flags and state schema
├── architecture_spec.md          # Detailed technical specification
│
├── backend/
│   ├── .env.example              # Environment variable template
│   ├── requirements.txt          # Python dependencies (pinned)
│   ├── perform_tests.py          # Pytest test suite (25 tests)
│   ├── tests/
│   │   ├── load_test_suite.py    # Async load testing (latency, RPS, error rate)
│   │   └── db_stress_suite.py    # DB saturation test (retrieval scaling)
│   └── app/
│       ├── main.py               # FastAPI app + CORS middleware
│       ├── core/
│       │   ├── models.py         # Pydantic schemas (ConfigState, etc.)
│       │   ├── state.py          # Global config singleton + lock
│       │   ├── firewall.py       # SemanticFirewall engine (pure math)
│       │   └── settings.py       # Environment-driven settings
│       ├── api/
│       │   └── routes.py         # HTTP routes (thin FastAPI layer)
│       └── modules/
│           ├── embedder.py       # BGE-M3 embedding singleton
│           ├── storage.py        # LanceDB vector store
│           └── ingestor.py       # PDF chunking pipeline
│
└── frontend/
    ├── package.json
    └── src/
        ├── App.tsx               # Main layout + ErrorBoundary wrappers
        ├── config.ts             # Centralized API URL (env-driven)
        ├── store.ts              # Zustand state management
        └── components/
            ├── ControlPanel.tsx   # Firewall sliders + pipeline ordering
            ├── ChatInterface.tsx  # Chat with firewall toggle support
            ├── AuditPanel.tsx     # Query audit + activation inspector
            ├── TelemetryHUD.tsx   # System metrics display
            └── ErrorBoundary.tsx  # React error boundary (per-component isolation)
```

---

## API Reference

All endpoints are served at `http://localhost:8000`.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/chat` | API Key* | Send a prompt through the firewall pipeline. Streaming NDJSON response. |
| `POST` | `/audit` | API Key* | Test a query against the corpus. Returns activation count and nearest vector. |
| `POST` | `/galaxy/config` | API Key* | Update firewall configuration (thresholds, orders, factor). |
| `POST` | `/corpus/upload-pdf` | — | Upload a PDF for async vectorization into LanceDB. |
| `GET` | `/corpus/task-status/{id}` | — | Poll PDF ingestion task progress. |
| `GET` | `/corpus/packs` | — | List all uploaded document packs with chunk counts. |
| `DELETE` | `/corpus/packs/{filename}` | — | Remove a document pack from the vector store. |
| `GET` | `/system/stats` | — | CPU, RAM, GPU utilization metrics. |
| `GET` | `/health` | — | Liveness probe: embedder status, corpus size, UTC timestamp. |

*\* API Key required only if `FIREWALL_API_KEY` environment variable is set.*

---

## Security

This system implements multiple defense layers:

1. **Semantic Firewall** — Three-stage vector validation pipeline with short-circuit evaluation.
2. **Anti-Piggybacking** — Language-agnostic clause segmentation prevents malicious prompt injection via appended instructions.
3. **Strict RAG Confinement** — LLM system prompt constrains responses exclusively to corpus context.
4. **CORS Hardening** — Explicit origin allowlist, no wildcard credentials.
5. **API Key Authentication** — Opt-in header-based auth for mutation endpoints.
6. **Input Sanitization** — 4000-character prompt limit enforced at schema level before vectorization.
7. **Atomic Configuration** — Frozen Pydantic models + async lock prevent race conditions on concurrent config updates.
8. **Pipeline Order Validation** — Duplicate filter priorities are rejected at the schema level.
9. **PDF Upload Hardening** — 50 MB size limit, PDF magic-byte validation, filename sanitization against path traversal.
10. **SQL Injection Prevention** — Filename whitelist regex + quote escaping on all storage layer queries.
11. **Structured Logging** — All modules use Python `logging` with severity levels. Client-facing error messages are generic (no stack traces leaked).
12. **Fail-Fast Configuration** — `pydantic-settings` validates all env vars at boot. Invalid types or out-of-range values crash the app immediately instead of producing silent failures. `FIREWALL_API_KEY` uses `SecretStr` to prevent accidental exposure in logs or tracebacks.
13. **Repository Hygiene** — `.env` is excluded via root `.gitignore` to prevent accidental secret commits.

---

## License

Proprietary. All rights reserved. Threepwood INtelligence.
