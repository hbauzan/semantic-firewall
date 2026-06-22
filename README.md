# Three-Headed Semantic Firewall

A local-first RAG security layer that validates query-to-corpus geometric alignment across 1024 dimensions before routing to an LLM. Three independent filters — Noise, Cosine, and Excitation — execute in a user-defined sequence. Any single failure blocks the entire prompt.

Built for sovereign AI deployments where data never leaves the machine.

> **Version:** v2.33.1 | **Model:** BAAI/bge-m3 (1024D) | **LLM:** Ollama / OpenAI / Anthropic / Google / Groq | **DB:** LanceDB

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
- [Transparent Proxy (OpenAI V1 Spec)](#transparent-proxy-openai-v1-spec)
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

         ── OR ──

┌─────────────────────────────────────────────────┐
│  /v1/chat/completions (OpenAI-compatible proxy)  │
│  Same firewall pipeline → Provider abstraction   │
└─────────────────────────────────────────────────┘
```

**Three Filters:**

| # | Filter | What it checks | Blocks when |
|---|--------|---------------|-------------|
| 1 | **Noise Pre-Filter** | Average absolute delta across all 1024 dims | `avg_delta > global_noise_limit` |
| 2 | **Cosine Filter** | Cosine similarity between query and corpus vectors | `cos(Q, C) < cosine_threshold` |
| 3 | **Excitation Filter** | Count of dimensions where `|Q_i - C_i| <= noise_tolerance` | `activations < excitation_threshold` |

Execution order is configurable at runtime via the HUD. If Filter 1 blocks, Filters 2 and 3 never execute.

**Two operating modes:**

| Mode | Corpus role | First filter that detects similarity | First filter that detects divergence |
|------|------------|--------------------------------------|--------------------------------------|
| **Positive** (default) | Allowlist — only corpus topics pass | OK, continue | **BREACH**, short-circuit |
| **Negative** | Denylist — corpus topics are blocked | **BREACH**, short-circuit | OK, continue |

In **positive mode**, the corpus defines what's allowed — queries must be similar. In **negative mode**, the corpus defines what's restricted — the first filter that detects similarity blocks immediately.

---

## Prerequisites

| Dependency | Version | Purpose |
|-----------|---------|---------|
| **Python** | 3.14+ | Backend (FastAPI, embeddings, vector math). Managed by `uv` — no manual venv needed. |
| **uv** | Latest | Backend toolchain (dependencies, venv, execution). Source of truth: `backend/pyproject.toml`. |
| **Node.js** | 20+ | Frontend runtime (React 19, Vite). |
| **pnpm** | 9+ | Frontend package manager. Source of truth: `frontend/pnpm-lock.yaml`. |
| **Ollama** | Latest | Default local LLM provider (optional if you point at a cloud provider). |
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
uv sync
```

`uv sync` reads `pyproject.toml`, resolves the locked dependency set from `uv.lock`, and creates the `.venv` automatically. There is no manual virtual-environment activation and no `pip install` — every command runs through `uv run`. (`requirements.txt` is kept as a generated artifact for non-`uv` consumers, not as the source of truth.)

> **First run note:** The `BAAI/bge-m3` model (~2.3 GB) will be automatically downloaded by HuggingFace on first boot. This is a one-time operation.

### 3. Frontend setup

```bash
cd ../frontend
pnpm install
```

### 4. Make scripts executable (macOS/Linux)

```bash
cd ..
chmod +x run_commander.sh run_server.sh run_ui.sh run_tests.sh run_pack.sh
```

---

## Configuration

A single `.env` file in the **project root** configures both backend and frontend. The backend reads it via `pydantic-settings` at runtime; the frontend reads it via Vite at build time. No `source`, no `export` — just drop the file and start.

```bash
cp .env.example .env
# Edit .env with your values — both backend and frontend read from this single file.
```

> **If a variable has an invalid type or fails validation, the backend crashes immediately with a clear error.** This prevents silent misconfigurations from reaching production.

**Backend variables** (loaded by `pydantic-settings`):

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS origins. Use `*` only for development. |
| `FIREWALL_API_KEY` | *(unset)* | If set, all `/chat`, `/audit`, and `/galaxy/config` endpoints require `X-API-Key` header. Stored as `SecretStr` — never leaked to logs. Leave unset for open local development. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API endpoint. |
| `OLLAMA_MODEL` | `llama3.1` | LLM model name for inference. |
| `EMBEDDING_MODEL` | `BAAI/bge-m3` | HuggingFace embedding model ID. Change only if you reindex the corpus. |
| `MAX_UPLOAD_MB` | `50` | Maximum PDF upload size in megabytes (1–500). |
| `CHUNK_SIZE` | `2048` | PDF chunking size in characters (100–10000). |
| `CHUNK_OVERLAP` | `200` | Overlap between consecutive chunks (0–2000). |
| `EMBEDDING_BATCH_SIZE` | `10` | Embeddings per batch during ingestion (1–100). |
| `RAG_TOP_K` | `3` | Number of corpus chunks retrieved for RAG context (1–10). |
| `RATE_LIMIT_CHAT` | `30/minute` | Rate limit for `/chat` and `/audit` endpoints per client IP. |
| `RATE_LIMIT_DEFAULT` | `60/minute` | Rate limit for all other endpoints per client IP. |
| `RATE_LIMIT_UPLOAD` | `10/minute` | Rate limit for `/corpus/upload-pdf` per client IP. |
| `HOST` | `0.0.0.0` | Bind address for uvicorn. Use `127.0.0.1` behind a reverse proxy. |
| `PORT` | `8000` | Backend listen port (1–65535). |
| `RELOAD` | `false` | Hot-reload on code changes. Set to `true` for development only. |

**Frontend variables** (loaded by Vite — must be prefixed with `VITE_`):

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Backend API endpoint used by all frontend components. |

**For local development, no `.env` file is required.** All defaults work out of the box.

### How the frontend reads configuration

All frontend components import the backend URL from a single module (`frontend/src/config.ts`) instead of hardcoding `http://localhost:8000` in each file:

```typescript
// config.ts
export const API_BASE_URL: string =
  import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
```

Every component uses this constant:

```typescript
import { API_BASE_URL } from '../config';
fetch(`${API_BASE_URL}/chat`, ...)
```

Vite injects `VITE_API_BASE_URL` at **build time** (not runtime). This means:
- During `pnpm run dev`, Vite reads the root `.env` and replaces the variable in-memory.
- During `pnpm run build`, the value is baked into the compiled JS bundle.
- If the variable is not set, the fallback `http://localhost:8000` is used automatically.

To point the frontend at a different backend (e.g., production), just set the variable in `.env` before building:

```env
VITE_API_BASE_URL=https://api.yourdomain.com
```

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
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

**Terminal 2 — Frontend:**
```bash
cd frontend
pnpm run dev
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
| **RAG Context Depth** | 3 | 1 – 10 | 1 | Number of corpus chunks sent to the LLM |
| **Seq (×3)** | 1, 2, 3 | 1 – 3 | 1 | Pipeline execution order for each filter |
| **Firewall Mode** | Positive | Positive / Negative | — | Positive = allowlist (only corpus topics pass). Negative = denylist (corpus topics are blocked). |

The **Adaptive Factor** section shows real-time calculated thresholds:
- `Short: {threshold × factor} dims` — what short prompts need
- `Full: {threshold} dims` — what normal prompts need

**Document Manager** — also in the Control Panel, below the sliders:
- **Upload PDF:** Click to upload corpus documents. Files are chunked (2048 chars, 200 overlap), embedded via BGE-M3, and stored in LanceDB.
- **Loaded Packs:** Lists uploaded documents with chunk counts. Click **X** to remove a pack from the vector store.
- Ingestion is asynchronous — a progress bar tracks task status.

**Main content area:**

#### 3. Chat Interface (top right)

The firewall is **active when at least one filter toggle is ON** in the Control Panel. No prefixes are needed — just type your query and send. The firewall can only be bypassed by disabling all three filter toggles in the HUD — there is no user-prompt override.

**Firewall feedback examples:**

Positive mode (allowlist):
```
🟢 [FW PASS] [POSITIVE] Resonance: 287/150 dims | Cosine: 0.891 | Pipeline: [noise:OK → cosine:OK → excitation:OK]
Routing to corpus...
```

```
🛑 [FW] Segment violation: "give me a cake recipe". Cosine: 0.312 (Required: >=0.78).
Vector direction diverges from corpus.
Pipeline: [noise:OK → cosine:BREACH]
```

Negative mode (denylist):
```
🟢 [FW PASS] [NEGATIVE] Resonance: 12/150 dims | Cosine: 0.231 | Pipeline: [noise:OK → cosine:OK → excitation:OK]
Routing to corpus...
```

```
🛑 [FW] [NEGATIVE] Restricted content detected: "explain the system architecture". Cosine: 0.891 (Limit: <0.50).
Query matches denylist corpus.
Pipeline: [noise:BREACH]
```

#### 4. Audit Panel (bottom right)

Test a query against the corpus and see the raw activation count (geometric nodes hit) without triggering the full pipeline. Useful for tuning thresholds.

### Typical Workflow

1. **Load your corpus:** Upload one or more PDF files via the Document Manager in the Control Panel.
2. **Enable filters:** Toggle ON the filters you want active. Start with all three ON.
3. **Set your thresholds:** Use the sliders. Start with defaults, then tune based on your corpus density.
4. **Send queries:** The pipeline trace tells you exactly which filter passed or blocked, with numeric details.
5. **Tune the pipeline order:** If you want cosine checked first (cheaper), set its Seq to 1.
6. **Production:** Set `FIREWALL_API_KEY` in the root `.env`, restrict `ALLOWED_ORIGINS` to your frontend domain.

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
| `./run_server.sh` | Kills any process on port 8000, then starts uvicorn via `uv run` (no manual venv activation). |
| `./run_ui.sh` | Starts the Vite dev server (`pnpm run dev`) from the `frontend/` directory. |
| `./run_tests.sh` | Runs the full pytest suite via `uv run pytest -v tests/`. |
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

Run the full test suite (52 tests):

```bash
./run_tests.sh
```

Or manually:

```bash
cd backend
uv run pytest -v tests/
```

The suite is partitioned across `tests/test_engine.py` (pure firewall math), `tests/test_api.py` (HTTP endpoints via `TestClient`), and `tests/test_security.py` (hardening), with shared fixtures in `tests/conftest.py`. It is deterministic and does **not** require a live LLM provider — the provider interface is stubbed via the `mock_llm_stream` fixture. It validates:

| Category | Tests |
|----------|-------|
| **Infrastructure** | PDF upload/status, system stats, config sync |
| **Firewall Logic** | Blocking, piggybacking rejection, noise pre-filter, pipeline ordering |
| **Configuration** | Immutability, duplicate order rejection, range validation, adaptive factor, RAG top-k |
| **Engine (unit)** | Segmentation, overflow chunking, clause evaluation pass/breach |
| **Security** | Prompt length limits, API key enforcement |
| **Proxy** | OpenAI v1 spec compliance, firewall interception on proxy, SSE streaming, graceful upstream-failure handling |
| **Health** | Health check endpoint response shape |

### Load Testing

An async load test suite extracts hard performance metrics under concurrent load. **The backend must be running before launching the suite.**

```bash
# Terminal 1 — start the server
./run_server.sh

# Terminal 2 — run the load tests
cd backend
uv run python tests/load_test_suite.py
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
uv run python tests/db_stress_suite.py
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
├── .env.example                  # Environment variable template (backend + frontend)
├── .gitignore                    # Excludes .env, __pycache__, node_modules, etc.
├── run_commander.sh              # Interactive TUI launcher
├── run_server.sh                 # Backend startup script (auto-kills port 8000)
├── run_ui.sh                     # Frontend startup script
├── run_tests.sh                  # Test runner script
├── run_pack.sh                   # Source code bundler (generates context.txt)
├── semantic_guardtrails_packager.py  # Packager logic used by run_pack.sh
├── manifest.json                 # Feature flags and state schema (version ledger)
├── architecture_spec.md          # Detailed technical specification
├── CONTEXT.md                    # Domain glossary (ubiquitous language)
│
├── backend/
│   ├── pyproject.toml            # Dependency source of truth ([project]) + pytest config
│   ├── uv.lock                   # Locked dependency set (uv)
│   ├── requirements.txt          # Generated artifact (uv pip compile) — not the source of truth
│   ├── tests/
│   │   ├── conftest.py           # Shared fixtures (TestClient, mock_llm_stream, config reset)
│   │   ├── test_engine.py        # Engine unit tests (pure firewall math)
│   │   ├── test_api.py           # HTTP endpoint tests via TestClient
│   │   ├── test_security.py      # Security hardening tests
│   │   ├── load_test_suite.py    # Async load testing (latency, RPS, error rate)
│   │   └── db_stress_suite.py    # DB saturation test (retrieval scaling)
│   └── app/
│       ├── main.py               # FastAPI app + CORS + security headers + rate limiting
│       ├── core/
│       │   ├── models.py         # Pydantic schemas (ConfigState, etc.)
│       │   ├── state.py          # Global config singleton + lock
│       │   ├── firewall.py       # SemanticFirewall engine (pure math)
│       │   ├── logging_config.py # Rotating logger setup
│       │   └── settings.py       # Environment-driven settings
│       ├── api/
│       │   ├── router_main.py    # Aggregates the endpoint routers
│       │   └── endpoints/        # Decomposed routers: chat, config, corpus, system, _shared
│       └── modules/
│           ├── embedder.py       # BGE-M3 embedding singleton
│           ├── storage.py        # LanceDB vector store
│           ├── ingestor.py       # PDF chunking pipeline
│           ├── sniffer.py        # Real-Time Semantic Sniffer (RTSS) + trace persistence
│           ├── persistence.py    # Chat history persistence
│           ├── profiles.py       # Config profile save/load
│           └── providers/        # base.py (ABC) + ollama, openai, anthropic, google, groq
│
└── frontend/
    ├── package.json
    ├── pnpm-lock.yaml
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

## Transparent Proxy (OpenAI V1 Spec)

The firewall exposes a `POST /v1/chat/completions` endpoint that implements the OpenAI chat completions spec. Any tool, SDK, or agent framework that speaks the OpenAI protocol can drop in the firewall as its base URL — zero code changes required on the client side.

### How it works

1. The proxy receives a standard OpenAI `messages` array.
2. The **last message** is extracted and passed through the full segmentation + firewall pipeline (same as `/chat`).
3. If **any clause fails any filter**, the proxy returns a `403 Forbidden` in the OpenAI standard error format:
   ```json
   {
     "error": {
       "message": "🛑 [FW] Segment violation: cosine",
       "type": "security_breach",
       "code": "403"
     }
   }
   ```
4. If all clauses pass, the request is forwarded to the configured LLM provider and streamed back as **Server-Sent Events (SSE)** in the OpenAI `data: {...}\n\n` format, terminated by `data: [DONE]\n\n`.

### Provider Abstraction

LLM routing is abstracted behind a `BaseProvider` interface (`app/modules/providers/base.py`). The initial implementation is `OllamaProvider`, which maps the OpenAI message format to the Ollama `/api/generate` endpoint and converts the response stream back to OpenAI SSE chunks. Adding a new provider (vLLM, llama.cpp server, etc.) means implementing a single `stream_chat` async generator.

### Usage example

Point any OpenAI-compatible client at the firewall:

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-firewall-api-key"   # or "not-needed" if FIREWALL_API_KEY is unset
)

response = client.chat.completions.create(
    model="llama3.1",
    messages=[{"role": "user", "content": "Explain the system architecture"}],
    stream=True
)

for chunk in response:
    print(chunk.choices[0].delta.content, end="")
```

If the prompt violates the firewall, the client receives a 403 with a structured error instead of a completion.

---

## API Reference

All endpoints are served at `http://localhost:8000`.

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| `POST` | `/v1/chat/completions` | API Key* | OpenAI-compatible proxy. Firewall intercepts the last message; streams SSE response. |
| `POST` | `/chat` | API Key* | Send a prompt through the firewall pipeline. Streaming NDJSON response. |
| `POST` | `/audit` | API Key* | Test a query against the corpus. Returns activation count and nearest text match. |
| `POST` | `/galaxy/config` | API Key* | Update firewall configuration (thresholds, orders, factor). |
| `POST` | `/corpus/upload-pdf` | API Key* | Upload a PDF for async vectorization into LanceDB. |
| `GET` | `/corpus/task-status/{id}` | API Key* | Poll PDF ingestion task progress. |
| `GET` | `/corpus/packs` | API Key* | List all uploaded document packs with chunk counts. |
| `DELETE` | `/corpus/packs/{filename}` | API Key* | Remove a document pack from the vector store. |
| `GET` | `/system/stats` | API Key* | CPU, RAM, GPU utilization metrics. |
| `GET` | `/health` | — | Liveness probe: status and UTC timestamp. Minimal response — no internal state exposed. |

*\* API Key required only if `FIREWALL_API_KEY` environment variable is set.*

---

## Security

Security hardening measures applied to the application infrastructure:

1. **CORS Hardening** — Explicit origin allowlist, no wildcard credentials. Credentials are auto-disabled when `*` is configured.
2. **API Key Authentication** — Opt-in header-based auth. When enabled, protects all endpoints except `/health`. Comparison uses `hmac.compare_digest` (constant-time, timing-attack safe).
3. **Input Sanitization** — 4000-character prompt limit enforced at schema level before vectorization.
4. **Atomic Configuration** — Frozen Pydantic models + async lock prevent race conditions on concurrent config updates.
5. **Pipeline Order Validation** — Duplicate filter priorities are rejected at the schema level.
6. **PDF Upload Hardening** — Configurable size limit (default 50 MB), streamed read with early rejection (never loads full payload into RAM), PDF magic-byte validation, filename sanitization against path traversal.
7. **SQL Injection Prevention** — Filename whitelist regex + quote escaping on all storage layer queries.
8. **Structured Logging** — All modules use Python `logging` with severity levels. Client-facing error messages are generic (no stack traces or internal URLs leaked).
9. **Fail-Fast Configuration** — `pydantic-settings` validates all env vars at boot. Invalid types or out-of-range values crash the app immediately. `FIREWALL_API_KEY` uses `SecretStr` to prevent accidental exposure in logs. Startup warning logged when API key is not configured.
10. **Repository Hygiene** — `.env`, runtime interception data (`backend/data/*.json`), logs (`backend/logs/`), the vector store (`lancedb_data/`), and the generated source bundle (`context.txt`) are all excluded via root `.gitignore`. No intercepted prompts, responses, or secrets are tracked in git.
11. **Security Headers** — All responses include `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Content-Security-Policy: frame-ancestors 'none'`, `Referrer-Policy`, `Permissions-Policy`, and `Strict-Transport-Security` (HSTS, 2-year max-age).
12. **DoS Mitigation** — Concurrent PDF ingestion capped at 3 threads via semaphore. Ollama streaming has a 300-second read timeout. Upload size enforced during chunked read (before full allocation).
13. **Data Integrity** — Storage ID generation is serialized via `threading.Lock` to prevent duplicate IDs from concurrent uploads.
14. **Protocol Safety** — Frontend API URL fallback inherits the page's protocol (`https://` in production) instead of hardcoding `http://`.
15. **Rate Limiting** — Per-IP rate limits via `slowapi`: `/chat` and `/audit` at 30/min, `/corpus/upload-pdf` at 10/min, all other endpoints at 60/min. Configurable via `.env`. Returns HTTP 429 when exceeded.
16. **LLM Response Validation** — Ollama streaming validates HTTP status code and JSON format on every line before forwarding to the client. Malformed lines are dropped and logged.
17. **Conditional Swagger Docs** — `/docs` and `/redoc` are automatically disabled when `FIREWALL_API_KEY` is set, preventing schema enumeration in production.
18. **Minimal Health Endpoint** — `/health` returns only `status` and `timestamp`. No internal state (embedder status, corpus size) is exposed to unauthenticated callers.

### API Key Authentication

The `FIREWALL_API_KEY` variable is an **opt-in** authentication layer for the backend's sensitive endpoints.

**Disabled (default — local development):** When the variable is not set, all endpoints are open. Any process that can reach port 8000 can send queries, change firewall configuration, and upload PDFs. This is the expected behavior for local development.

**Enabled (production):** Add the variable to the root `.env`:

```env
FIREWALL_API_KEY=your-secret-key-here
```

Once set, **all endpoints except `/health`** require every request to include the header:

```
X-API-Key: your-secret-key-here
```

Requests without the header, or with an incorrect key, receive a **403 Forbidden** response. Only `/health` remains open (for load balancer probes).

**Protected endpoints:**

| Endpoint | Requires API Key |
|----------|:---:|
| `POST /v1/chat/completions` | Yes |
| `POST /chat` | Yes |
| `POST /audit` | Yes |
| `POST /galaxy/config` | Yes |
| `POST /corpus/upload-pdf` | Yes |
| `GET /corpus/packs` | Yes |
| `DELETE /corpus/packs/{filename}` | Yes |
| `GET /corpus/task-status/{id}` | Yes |
| `GET /system/stats` | Yes |
| `GET /health` | No |

The key comparison uses `hmac.compare_digest` (constant-time) to prevent timing side-channel attacks. The key is stored internally as a Pydantic `SecretStr` — if the settings object is accidentally logged or printed, the value appears as `**********` instead of the real key.

To disable the key, comment out or remove the line from `.env` and restart the backend.

---

## License

Proprietary. All rights reserved. Threepwood INtelligence.
