# Phase-Lock Semantic Firewall Architecture Specification

## 1. Dimensional Excitation Firewall (FED Math)
The firewall operates by evaluating the raw 1024D embedding layers produced by `BAAI/bge-m3` between a given Query Vector (`Q`) and a Context Vector from the nearest knowledge entry (`C`).
- **Delta Calculation:** For each dimension `i`, we compute the absolute delta `Delta_i = abs(Q_i - C_i)`.
- **Activation Logic:** An activation register is tripped if `Delta_i` is less than or equal to the `Noise Tolerance` configuration (default 0.005). Thus, `Activation_i = 1`.
- **Gate:** The final dimension sum `sum(Activation_i)` must be mathematically greater than or equal to the `Excitation Threshold` (default 150) to be deemed geometrically 'SAFE'. Otherwise, the request triggers a `SECURITY BREACH` and the streaming block breaks connection.
- **Explicit Chat Feedback:** When any firewall filter is enabled, the chat endpoint injects human-readable telemetry into the response. A blocked query returns `🛑 [FW] Segment violation` with the exact metric that triggered the breach. A passed query prepends `🟢 [FW PASS]` with resonance/threshold and cosine values before routing to the LLM stream. All telemetry uses language-neutral technical terms.

## 2. Backend Architecture
Utilizes **FastAPI** for route management yielding high execution throughput. The backend follows a **layered separation of concerns**:

```
app/
├── core/                    # Framework-agnostic logic
│   ├── models.py            # Pydantic models (ConfigState, ConfigUpdate, etc.)
│   ├── state.py             # Global config singleton + asyncio.Lock + set_config()
│   ├── firewall.py          # SemanticFirewall engine (pure vector math)
│   └── settings.py          # Environment-driven settings (Ollama, embedder, chunks)
├── api/
│   └── routes.py            # Thin FastAPI layer (HTTP, streaming, telemetry)
└── modules/
    ├── embedder.py          # BGE-M3 embedding singleton
    ├── storage.py           # LanceDB vector store
    └── ingestor.py          # PDF chunking pipeline + TaskStore with TTL
```

- **Firewall Engine (`core/firewall.py`):** `SemanticFirewall` class with static methods — completely agnostic of web framework, embedders, and storage. Receives numpy arrays and a frozen `ConfigState`, returns structured results. Portable for CLI tools, batch audits, or alternative API wrappers. Contains: `segment()`, `run_noise_filter()`, `run_cosine_filter()`, `run_excitation_filter()`, `build_pipeline()`, `evaluate_clause()`.
- **Models (`core/models.py`):** All Pydantic schemas. `ConfigState` is a **frozen BaseModel** — immutable after construction. `Field` constraints enforce value ranges. `@model_validator` ensures pipeline order uniqueness.
- **State (`core/state.py`):** Configuration singleton + `asyncio.Lock` for serialized writes. `set_config()` is an **async** function that acquires the lock before performing merge-validate-swap, guaranteeing no concurrent config corruption. A separate `set_config_sync()` exists for single-threaded test harnesses only. Each request handler snapshots the reference at entry (`cfg = config_state`) for mid-request consistency.
- **Routes (`api/routes.py`):** Thin HTTP layer — request parsing, embedding calls, storage queries, telemetry formatting, streaming responses. Delegates all firewall math to `SemanticFirewall`.
- **Embedder Singleton (`modules/embedder.py`):** Automatically maps Tensor operations sequentially to Apple Silicon (`MPS`), Nvidia (`CUDA`), or fallback CPU. The model name is configurable via `EMBEDDING_MODEL` env var.
- **Storage Layer (`modules/storage.py`):** Serverless **LanceDB** vector store ensuring BigInt capacity on IDs natively structured via `LanceModel` (id, vector, text, metadata). Implements native JSON metadata grouping for dynamic **Document Management** (`get_summary`, `delete_pack`) allowing live corpus curation. Filename validation prevents SQL injection on delete operations.
- **Ingestor Protocol (`modules/ingestor.py`):** Employs `PyMuPDF` iteratively with Python `asyncio.to_thread` for non-blocking chunking routines. Chunk size, overlap, and batch size are configurable via `CHUNK_SIZE`, `CHUNK_OVERLAP`, `EMBEDDING_BATCH_SIZE` env vars (defaults: 2048, 200, 10). Completed/failed tasks are automatically pruned after 1 hour (`TaskStore` with TTL).
- **Settings (`core/settings.py`):** Centralized environment-driven configuration. All previously hardcoded values (Ollama URL, model name, embedding model, chunk parameters) are read from environment variables with sensible defaults. See `.env.example` for the full list.

## 3. Execution Pipeline (Sequential Reorderable Firewall)
The firewall executes three distinct validation stages in a **user-defined sequence** controlled via the HUD's `Seq` inputs. The pipeline is constructed at evaluation time by sorting the three stages based on their integer priority values:

| Stage | Filter | Config Key | Default Order |
|-------|--------|------------|---------------|
| A | **Noise Pre-Filter** | `noise_order` | 1 |
| B | **Cosine Filter** | `cosine_order` | 2 |
| C | **Excitation Filter** | `excitation_order` | 3 |

**Stage A — Cosine Filter:** Traditional cosine similarity gate. Computes `cos(Q, C) = dot(Q, C) / (‖Q‖ × ‖C‖)` using **raw vectors** (no normalization). Blocks if `cos(Q, C) < cosine_threshold`.

**Stage B — Excitation Filter:** Dimensional resonance count. For each of 1024 dimensions, counts activations where `|Q_i - C_i| <= noise_tolerance`. Uses **raw vectors**. Applies the adaptive threshold (see Section 4). Blocks if `activations < threshold`.

**Stage C — Noise Pre-Filter (Global Delta Sanity):** Computes the average absolute delta across all 1024 dimensions: `avg_delta = np.mean(np.abs(Q - C))`. If `avg_delta > global_noise_limit`, the query is blocked immediately. This catches gross semantic drift before finer-grained filters run.

**Execution semantics:** Stages are sorted by their `_order` integer (ascending). If Stage N returns BREACH, Stages N+1..3 are **never evaluated**. Each clause from the segmentation defense (Section 5) must independently pass the **entire** ordered pipeline. Telemetry trace format: `Pipeline: [cosine:OK → excitation:OK → noise:OK]` or `[cosine:OK → excitation:BREACH]`.

## 4. Adaptive Clause Logic
When the hybrid segmentation engine (Section 6.1) splits a prompt into clauses, short clauses receive a relaxed excitation threshold to avoid false positives on terse but legitimate queries.

- **Config:** `adaptive_factor` (float, default 0.85, range 0.01–1.00). User-adjustable via HUD slider.
- **Rule:** If a clause contains **fewer than 6 words**, the excitation threshold is reduced by the adaptive factor: `current_threshold = excitation_threshold × adaptive_factor`.
- **Rationale:** Short phrases produce sparser embedding activations by nature. Without this multiplier, 2–5 word queries that are semantically valid would be rejected solely due to insufficient dimensional overlap.
- **Scope:** This adaptive reduction applies **only** within the Excitation Filter stage of the pipeline. Cosine and Noise filters use their full thresholds regardless of clause length.
- **HUD Feedback:** The ControlPanel displays real-time dimension requirements: `Short Query Req: {threshold × factor} dims` and `Full Query Req: {threshold} dims`.
- **Telemetry:** When a short clause triggers the adaptive path, the BREACH message includes: `[ADAPTIVE] Short Clause Detected. Applying {factor}x factor.`

## 5. Frontend Control Logic
- **State Management:** Overarched by **Zustand** React 19 Store maintaining configuration payloads (including `cosineOrder`, `excitationOrder`, `noiseOrder`, `globalNoiseLimit`, `adaptiveFactor`), an overarching `systemAction` global state, asynchronous ingestion states, chat histories, and per-second telemetry data points.
- **HUD Telemetry (`TelemetryHUD.tsx`):** Periodically polls `/system/stats` for PSUtil & CPU / Torch RAM mappings mapping system metrics underneath a custom ASCII-art **Pirate Monkey** multi-frame cycle. On Apple Silicon (MPS), GPU% is calculated as `torch.mps.current_allocated_memory() / psutil.virtual_memory().total * 100` — reflecting actual allocation against total unified memory. On CUDA, it uses `torch.cuda.memory_allocated() / torch.cuda.get_device_properties(0).total_mem * 100`.
- **Pipeline Ordering UI (`ControlPanel.tsx`):** Slider groups are visually ordered to match the default pipeline execution sequence: **Noise Pre-Filter (Seq 1)** → **Cosine Gate (Seq 2)** → **Excitation Threshold + Noise Tolerance (Seq 3)** → **Adaptive Factor**. Each filter includes a **Seq** numerical input (1–3) that controls pipeline execution order and an **ON/OFF toggle button** that enables or disables that individual filter. When a filter is toggled OFF, its slider group dims to 40% opacity and the filter is excluded from the pipeline entirely (via `build_pipeline()` in the engine). The firewall is considered active when at least one filter is enabled (`fw_on = noise_enabled || cosine_enabled || excitation_enabled`). The legacy `[FW=OFF]` prompt prefix is still supported as a bypass override. All values including enabled states are synced to the backend via debounced `POST /galaxy/config`.
- **Interface Guardrails (`ChatInterface.tsx`):** Uses `crypto.randomUUID()` for collision-free message IDs. Decodes raw NDJSON via `aiter_lines()` from the backend to guarantee seamless UTF-8 character stability for multi-byte accents organically. Each component is wrapped in an `ErrorBoundary` to prevent cascading UI crashes — a single panel failure renders a retry button instead of killing the entire app.
- **Centralized API Config (`config.ts`):** All API calls reference `API_BASE_URL` from `import.meta.env.VITE_API_BASE_URL` (default: `http://localhost:8000`). Zero hardcoded URLs in components.

## 6. Anti-Semantic Piggybacking Defense
Addresses the attack vector where a malicious or off-topic instruction is appended to an otherwise legitimate prompt, causing the averaged embedding to pass dimensional excitation while the piggybacked payload executes unchecked.

### 6.1 Language-Agnostic Structural Segmentation
Instead of vectorizing the full prompt as a single embedding, `chat_endpoint` splits the input into logical clauses via a **purely structural (symbol-only) regex** that carries zero language-specific dependencies:
```
re.split(r'[.!?;:\n\-\|«»\u201c\u201d]+', clean_prompt)
```
This splits on universal punctuation terminators (`.`, `!`, `?`, `;`, `:`, `\n`, `-`, `|`, `«»`, `""`) — no words from any language are referenced. Fragments ≤ 4 chars are discarded.

**Safety Fallback (Overflow Chunking):** If any resulting clause exceeds 20 words, it is force-split into sub-chunks of 15 words each. This prevents a long run-on sentence from averaging its embedding across safe and malicious content. Each sub-chunk must independently pass the entire ordered pipeline.

If **any single clause or sub-chunk** fails any stage of the pipeline, the entire prompt is rejected with `[FW] Segment violation`. This ensures a poisoned clause cannot hide inside benign context, regardless of input language.

### 6.2 System Prompt Hardening (Zero-Tolerance Context Confinement)
As a secondary defense layer, `stream_ollama` injects a strict system instruction constraining the LLM to respond **exclusively** from the provided RAG context. If a query or sub-instruction cannot be answered from the context (e.g. recipes, jokes, unrelated code), the LLM is instructed to refuse that portion. This provides defense-in-depth even if the segmentation firewall is bypassed.

## 7. API Security Hardening

### 7.1 CORS Policy
CORS is configured via the `ALLOWED_ORIGINS` environment variable (default: `http://localhost:5173`). The middleware enforces:
- **Explicit origins only** — no wildcard `*` in production. If `*` is used (dev only), `allow_credentials` is automatically set to `false` to prevent the browser credential leak anti-pattern.
- **Restricted methods** — only `GET`, `POST`, `DELETE` are allowed (no `PUT`, `PATCH`, `OPTIONS` beyond preflight).
- **Restricted headers** — only `Content-Type` and `X-API-Key` are accepted.

### 7.2 API Key Authentication (Opt-in)
When the `FIREWALL_API_KEY` environment variable is set, all mutation endpoints (`/chat`, `/audit`, `/galaxy/config`) require the `X-API-Key` header to match. Returns HTTP 403 on mismatch. If the variable is unset, all endpoints remain open for local development. Configuration is documented in `.env.example`.

### 7.3 Input Sanitization
All inbound prompts (`ChatRequest`, `AuditRequest`) are constrained to `PROMPT_MAX_LENGTH` (4000 characters) at the Pydantic schema level. Payloads exceeding this limit are rejected with HTTP 422 before any embedding computation occurs, preventing memory exhaustion attacks on the vectorization stage.

### 7.4 PDF Upload Hardening
The `/corpus/upload-pdf` endpoint enforces three-layer validation before accepting any file:
- **Size limit:** Files exceeding 50 MB are rejected with HTTP 413 before processing.
- **Magic-byte validation:** The first 4 bytes must match the PDF signature (`%PDF`). Non-PDF files are rejected with HTTP 400 regardless of the declared MIME type or file extension.
- **Filename sanitization:** Filenames are stripped to `os.path.basename()` (preventing path traversal), then validated against a whitelist regex (`[\w\s.\-()]+\.pdf`). Unsafe characters are replaced with underscores.

### 7.5 SQL Injection Prevention (Storage Layer)
The `delete_pack()` method in `storage.py` validates filenames against a whitelist regex before interpolating into the LanceDB SQL LIKE clause. Filenames containing quotes, semicolons, or other SQL metacharacters are rejected with a `ValueError`. Single quotes in valid filenames are escaped via SQL doubling (`'` → `''`).

### 7.6 Health Check Endpoint
`GET /health` returns the system's liveness status for load balancers, Kubernetes probes, and monitoring dashboards. Response includes:
- `status`: `"healthy"` (embedder loaded) or `"degraded"` (embedder missing).
- `timestamp`: UTC ISO 8601.
- `embedder_loaded`: boolean.
- `corpus_chunks`: total chunks in LanceDB.

### 7.7 Production Server Configuration
`main.py` reads `HOST`, `PORT`, and `RELOAD` from environment variables. `reload=True` is the default for development; production deployments should set `RELOAD=false`. Structured logging (`logging.basicConfig`) is initialized at app startup with `INFO` level.

### 7.8 Dependency Pinning
`requirements.txt` pins all production dependencies to exact versions (e.g. `fastapi==0.135.1`). This prevents silent breakage from upstream updates — particularly critical for `sentence-transformers` and `torch`, where version changes can alter embedding output and invalidate the entire corpus index.

### 7.9 Structured Logging
All backend modules use Python's `logging` module instead of `print()`. Log levels:
- `INFO` — successful operations (ingestion complete, model loaded).
- `WARNING` — non-fatal issues (malformed metadata, GPU telemetry unavailable, unsafe filename rejected).
- `ERROR` — recoverable failures (Ollama unreachable, invalid PDF).
- `CRITICAL` / `EXCEPTION` — unexpected failures with full traceback (ingestion crash).

Error messages returned to clients are generic and do not leak stack traces or internal paths.
