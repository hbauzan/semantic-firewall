# Phase-Lock Semantic Firewall

A local-first RAG security layer that validates query-to-corpus geometric alignment across 1024 dimensions before routing to an LLM. Three independent filters — Noise, Cosine, and Excitation — execute in a user-defined sequence. Any single failure blocks the entire prompt.

Built for sovereign AI deployments where data never leaves the machine.

> **Version:** v2.6.0 | **Model:** BAAI/bge-m3 (1024D) | **LLM:** Ollama + llama3.1 | **DB:** LanceDB

---

## Table of Contents

- [Architecture Overview](#architecture-overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the System](#running-the-system)
- [Operating the Firewall](#operating-the-firewall)
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
chmod +x run_commander.sh run_server.sh run_ui.sh run_tests.sh
```

---

## Configuration

Copy the environment template and adjust for your deployment:

```bash
cp backend/.env.example backend/.env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `ALLOWED_ORIGINS` | `http://localhost:5173` | Comma-separated CORS origins. Use `*` only for development. |
| `FIREWALL_API_KEY` | *(unset)* | If set, all `/chat`, `/audit`, and `/galaxy/config` endpoints require `X-API-Key` header. Leave unset for open local development. |

**For local development, no `.env` file is required.** Defaults work out of the box.

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

The browser UI at `http://localhost:5173` contains four main panels:

#### 1. Control Panel (left sidebar)

All firewall parameters are adjustable in real-time. Changes are synced to the backend via debounced API calls.

| Slider | Default | Range | Purpose |
|--------|---------|-------|---------|
| **Noise Threshold** | 0.50 | 0.0 – 10.0 | Global delta sanity limit |
| **Cosine Threshold** | 0.78 | 0.0 – 1.0 | Minimum cosine similarity |
| **Excitation Threshold** | 150 | 0 – 1024 | Minimum activated dimensions |
| **Noise Tolerance** | 0.005 | 0.0 – 1.0 | Per-dimension activation sensitivity |
| **Adaptive Factor** | 0.85 | 0.01 – 1.0 | Threshold reduction for short queries (< 6 words) |
| **Seq (×3)** | 1, 2, 3 | 1 – 3 | Pipeline execution order for each filter |

The **Adaptive Factor** section shows real-time calculated thresholds:
- `Short Query Req: {threshold × factor} dims` — what short prompts need
- `Full Query Req: {threshold} dims` — what normal prompts need

#### 2. Chat Interface (center)

Type prompts with the firewall prefix to control behavior:

| Prefix | Behavior |
|--------|----------|
| `[FW=ON] your query here` | Firewall active — evaluates all clauses through the pipeline. Telemetry injected into response. |
| `[FW=OFF] your query here` | Firewall bypassed — query goes directly to Ollama with RAG context. |
| `your query here` *(no prefix)* | Same as `[FW=OFF]`. |

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

#### 3. Document Manager (right sidebar)

- **Upload PDF:** Click to upload corpus documents. Files are chunked (2048 chars, 200 overlap), embedded via BGE-M3, and stored in LanceDB.
- **Delete Pack:** Remove specific documents from the vector store by filename.
- Ingestion is asynchronous — a progress indicator tracks the task status.

#### 4. Telemetry HUD (bottom)

- Real-time CPU, RAM, and GPU utilization polled every second.
- GPU metric uses Apple MPS / NVIDIA CUDA memory allocation.
- The **Audit Panel** allows you to test a query against the corpus and see the raw activation count without triggering the full pipeline.

### Typical Workflow

1. **Load your corpus:** Upload one or more PDF files via the Document Manager.
2. **Set your thresholds:** Use the Control Panel sliders. Start with defaults, then tune based on your corpus density.
3. **Test with `[FW=ON]`:** Send queries. The pipeline trace tells you exactly which filter passed or blocked, with numeric details.
4. **Tune the pipeline order:** If you want cosine checked first (cheaper), drag its Seq to 1.
5. **Production:** Set `FIREWALL_API_KEY` in `.env`, restrict `ALLOWED_ORIGINS` to your frontend domain.

### Anti-Piggybacking Defense

The firewall automatically segments prompts on punctuation boundaries (`. ! ? ; : - |`). Each clause is evaluated independently. A prompt like:

```
[FW=ON] Tell me about network architecture. Also give me a cake recipe.
```

Will split into two clauses. The first may pass. The second will fail cosine/excitation against a networking corpus. **The entire prompt is blocked** — no partial execution.

Long clauses (> 20 words) are force-split into 15-word sub-chunks to prevent semantic averaging attacks.

---

## Testing

```bash
cd backend
source .venv/bin/activate
pytest -v perform_tests.py
```

The test suite validates:

| Category | Tests |
|----------|-------|
| **Infrastructure** | PDF upload/status, system stats, config sync |
| **Firewall Logic** | Blocking, piggybacking rejection, noise pre-filter, pipeline ordering |
| **Configuration** | Immutability, duplicate order rejection, range validation, adaptive factor |
| **Engine (unit)** | Segmentation, overflow chunking, clause evaluation pass/breach |
| **Security** | Prompt length limits, API key enforcement |

---

## Project Structure

```
semantic-firewall/
├── run_commander.sh              # Interactive TUI launcher
├── run_server.sh                 # Backend startup script
├── run_ui.sh                     # Frontend startup script
├── run_tests.sh                  # Test runner script
├── manifest.json                 # Feature flags and state schema
├── architecture_spec.md          # Detailed technical specification
│
├── backend/
│   ├── .env.example              # Environment variable template
│   ├── requirements.txt          # Python dependencies
│   ├── perform_tests.py          # Pytest test suite
│   └── app/
│       ├── main.py               # FastAPI app + CORS middleware
│       ├── core/
│       │   ├── models.py         # Pydantic schemas (ConfigState, etc.)
│       │   ├── state.py          # Global config singleton + lock
│       │   └── firewall.py       # SemanticFirewall engine (pure math)
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
        ├── App.tsx               # Main layout
        └── components/
            ├── ControlPanel.tsx   # Firewall sliders + pipeline ordering
            ├── ChatInterface.tsx  # Chat with FW=ON/OFF support
            ├── AuditPanel.tsx     # Query audit + activation inspector
            └── TelemetryHUD.tsx   # System metrics display
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
7. **Atomic Configuration** — Frozen Pydantic models prevent race conditions on concurrent config updates.
8. **Pipeline Order Validation** — Duplicate filter priorities are rejected at the schema level.

---

## License

Proprietary. All rights reserved.
