# Three-Headed Semantic Firewall Architecture Specification

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
- **Embedder Singleton (`modules/embedder.py`):** Automatically maps Tensor operations sequentially to Apple Silicon (`MPS`), Nvidia (`CUDA`), or fallback CPU. The model name is read from the `settings` singleton.
- **Storage Layer (`modules/storage.py`):** Serverless **LanceDB** vector store ensuring BigInt capacity on IDs natively structured via `LanceModel` (id, vector, text, metadata). Implements native JSON metadata grouping for dynamic **Document Management** (`get_summary`, `delete_pack`) allowing live corpus curation. Filename validation prevents SQL injection on delete operations.
- **Ingestor Protocol (`modules/ingestor.py`):** Employs `PyMuPDF` iteratively with Python `asyncio.to_thread` for non-blocking chunking routines. Chunk size, overlap, and batch size are read from the `settings` singleton (defaults: 2048, 200, 10). Completed/failed tasks are automatically pruned after 1 hour (`TaskStore` with TTL).
- **Settings (`core/settings.py`):** Uses `pydantic-settings` (`BaseSettings`) for typed, validated configuration following 12-Factor App principles. All env vars are declared in a single `Settings` class with type annotations, default values, and range constraints. The `.env` file is loaded automatically at boot — no `source` or manual export required. If a variable has an invalid type or fails validation, the app crashes immediately with a clear Pydantic error (fail-fast). Secrets (`FIREWALL_API_KEY`) use `SecretStr` to prevent accidental logging. A singleton `settings` instance is created at import time and imported by all modules. The backend and frontend share a single root-level `.env` file — see `.env.example` for the full list. Vite reads the same file via `envDir: '..'` in `vite.config.ts`.

## 3. Execution Pipeline (Sequential Reorderable Firewall)
The firewall executes three distinct validation stages in a **user-defined sequence** controlled via the HUD's `Seq` inputs. The pipeline is constructed at evaluation time by sorting the three stages based on their integer priority values:

| Stage | Filter | Config Key | Default Order |
|-------|--------|------------|---------------|
| A | **Noise Pre-Filter** | `noise_order` | 1 |
| B | **Cosine Filter** | `cosine_order` | 2 |
| C | **Excitation Filter** | `excitation_order` | 3 |

**Stage A — Noise Pre-Filter (Global Delta Sanity):** Computes the average absolute delta across all 1024 dimensions: `avg_delta = np.mean(np.abs(Q - C))`. If `avg_delta > global_noise_limit`, the query is blocked immediately. This catches gross semantic drift before finer-grained filters run.

**Stage B — Cosine Filter:** Traditional cosine similarity gate. Computes `cos(Q, C) = dot(Q, C) / (‖Q‖ × ‖C‖)` using **raw vectors** (no normalization). Includes zero-norm guard and `np.clip(raw, -1.0, 1.0)` for floating-point safety. Blocks if `cos(Q, C) < cosine_threshold`.

**Stage C — Excitation Filter:** Dimensional resonance count. For each of 1024 dimensions, counts activations where `|Q_i - C_i| <= noise_tolerance`. Uses **raw vectors**. Applies the adaptive threshold (see Section 4). Blocks if `activations < threshold`.

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
- **HUD Telemetry (`TelemetryHUD.tsx`):** Periodically polls `/system/stats` for PSUtil & CPU / Torch RAM mappings. Displays **Three Monkey Heads** (one per filter: Noise, Cosine, Excitation) — each head animates when its filter is enabled and goes dark when disabled, providing visual pipeline status. Also shows the current `systemAction` state and a compact telemetry line (CPU/RAM/GPU). On Apple Silicon (MPS), GPU% is calculated as `torch.mps.current_allocated_memory() / psutil.virtual_memory().total * 100` — reflecting actual allocation against total unified memory. On CUDA, it uses `torch.cuda.memory_allocated() / torch.cuda.get_device_properties(0).total_mem * 100`.
- **Pipeline Ordering UI (`ControlPanel.tsx`):** Slider groups are visually ordered to match the default pipeline execution sequence: **Noise Pre-Filter (Seq 1)** → **Cosine Gate (Seq 2)** → **Excitation Threshold + Noise Tolerance (Seq 3)** → **Adaptive Factor**. Each filter includes a **Seq** numerical input (1–3) that controls pipeline execution order and an **ON/OFF toggle button** that enables or disables that individual filter. When a filter is toggled OFF, its slider group dims to 40% opacity and the filter is excluded from the pipeline entirely (via `build_pipeline()` in the engine). The firewall is considered active when at least one filter is enabled (`fw_on = noise_enabled || cosine_enabled || excitation_enabled`). There is no user-prompt bypass — the firewall can only be disabled via the authenticated HUD toggles. All values including enabled states are synced to the backend via debounced `POST /galaxy/config`.
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
When the `FIREWALL_API_KEY` environment variable is set, **all endpoints except `/health`** require the `X-API-Key` header to match. Returns HTTP 403 on mismatch. If the variable is unset, all endpoints remain open for local development. Configuration is documented in `.env.example`.

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
`GET /health` returns a minimal liveness response for load balancers, Kubernetes probes, and monitoring dashboards. Response includes only:
- `status`: `"healthy"`.
- `timestamp`: UTC ISO 8601.

No internal state (embedder status, corpus size) is exposed. This is the only endpoint that does not require API key authentication when `FIREWALL_API_KEY` is set.

### 7.7 Production Server Configuration
`main.py` reads `HOST`, `PORT`, and `RELOAD` from environment variables. `reload=True` is the default for development; production deployments should set `RELOAD=false`. Structured logging (`logging.basicConfig`) is initialized at app startup with `INFO` level.

### 7.8 Dependency Pinning
`requirements.txt` pins all production dependencies to exact versions (e.g. `fastapi==0.135.1`). This prevents silent breakage from upstream updates — particularly critical for `sentence-transformers` and `torch`, where version changes can alter embedding output and invalidate the entire corpus index.

### 7.9 Rate Limiting
Per-IP rate limiting is enforced via `slowapi` (a FastAPI-compatible wrapper around `limits`). Three configurable tiers:
- `/chat` and `/audit`: `RATE_LIMIT_CHAT` (default: `30/minute`).
- `/corpus/upload-pdf`: `RATE_LIMIT_UPLOAD` (default: `10/minute`).
- All other endpoints: `RATE_LIMIT_DEFAULT` (default: `60/minute`).

When a client exceeds its limit, the server returns HTTP 429 (Too Many Requests). Rate limits are keyed on the client's remote IP address.

### 7.10 LLM Response Validation
`stream_ollama` validates every chunk from the Ollama inference server before forwarding it to the client:
- **Status code check:** If Ollama returns a non-200 status, the stream immediately yields a generic error message and terminates. No raw error payloads from the LLM reach the client.
- **JSON line validation:** Each NDJSON line is parsed through `json.loads()` before forwarding. Malformed lines are dropped and logged at WARNING level with a truncated preview (max 200 chars).

### 7.11 Conditional Swagger Documentation
When `FIREWALL_API_KEY` is set, both `/docs` (Swagger UI) and `/redoc` (ReDoc) are disabled (`docs_url=None`, `redoc_url=None`). This prevents unauthenticated schema enumeration in production deployments. In local development (no API key), docs remain accessible for convenience.

### 7.12 HSTS (HTTP Strict Transport Security)
All responses include `Strict-Transport-Security: max-age=63072000; includeSubDomains` (2-year duration). This instructs browsers to always use HTTPS for subsequent requests, preventing protocol downgrade attacks.

### 7.13 Structured Logging
All backend modules use Python's `logging` module instead of `print()`. Log levels:
- `INFO` — successful operations (ingestion complete, model loaded).
- `WARNING` — non-fatal issues (malformed metadata, GPU telemetry unavailable, unsafe filename rejected).
- `ERROR` — recoverable failures (Ollama unreachable, invalid PDF).
- `CRITICAL` / `EXCEPTION` — unexpected failures with full traceback (ingestion crash).

Error messages returned to clients are generic and do not leak stack traces or internal paths.

## 8. Performance Testing

### 8.1 Async Load Test Suite (`tests/load_test_suite.py`)
An asyncio + httpx-based load testing harness that extracts hard performance metrics from the `/audit` endpoint under concurrent load. The suite is self-contained (no external load testing tools required).

**Three Payload Profiles:**

| Profile | Words | Triggers |
|---------|-------|----------|
| `short_query` | < 5 | Adaptive factor threshold reduction |
| `long_query` | > 50 | Multi-clause segmentation (punctuation split) |
| `overflow_query` | > 100, no punctuation | 15-word overflow chunking fallback |

**Concurrency Levels:** 10, 50, and 200 simultaneous connections per profile.

**Metrics Collected:**
- **Latency:** Min, Average, P95, Max (milliseconds).
- **Throughput:** Requests per Second (RPS).
- **Reliability:** HTTP 200 success count, HTTP 4xx/5xx failure count, timeouts, error rate %.

**Output:** Formatted console table + `metrics_report.csv` for documentation and CI integration.

### 8.2 Vector DB Bulk Saturation Test (`tests/db_stress_suite.py`)
Measures how retrieval latency and firewall evaluation time scale as the LanceDB knowledge base grows. Uses a temporary isolated database (cleaned up after each run) to avoid polluting the production corpus.

**Methodology:**
- **Mock Data Generator:** Produces synthetic 1024D unit-norm vectors and pseudo-random technical text chunks. The `--use-embedder` flag enables real BGE-M3 embeddings for higher fidelity (at the cost of speed).
- **Incremental Injection:** Vectors are injected in configurable batches (default 500). The database grows through milestones without being rebuilt.
- **Retrieval Benchmark:** At each milestone, a fixed pool of 100 query vectors fires through `table.search(vector).limit(1)`, isolating LanceDB search latency.
- **Firewall Benchmark:** Each retrieved vector pair is then evaluated through `SemanticFirewall.evaluate_clause()` with the default `ConfigState`, isolating pure firewall math cost.

**Default Milestones:** 1,000 → 10,000 → 50,000 rows.

**Metrics Collected (per milestone):**
- **Retrieval:** Avg, P95, Max latency (milliseconds).
- **Firewall:** Avg, P95, Max evaluation time (milliseconds).
- **Injection:** Total time to fill the DB to that milestone (seconds).

**Output:** Formatted console table + `tests/db_scaling_metrics.md` Markdown report with graph-ready tables (DB Size vs Avg Retrieval vs Avg Firewall vs Injection Time).
