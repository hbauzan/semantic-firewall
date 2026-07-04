# Three-Headed Semantic Firewall Architecture Specification

## 1. Dimensional Excitation Firewall (FED Math)
The firewall operates by evaluating the raw 1024D embedding layers produced by `BAAI/bge-m3` between a given Query Vector (`Q`) and a Context Vector from the nearest knowledge entry (`C`).
- **Delta Calculation:** For each dimension `i`, we compute the absolute delta `Delta_i = abs(Q_i - C_i)`.
- **Activation Logic:** An activation register is tripped if `Delta_i` is less than or equal to the `Noise Tolerance` configuration (default 0.005). Thus, `Activation_i = 1`.
- **Gate:** The final dimension sum `sum(Activation_i)` must be mathematically greater than or equal to the `Excitation Threshold` (default 150) to be deemed geometrically 'SAFE'. Otherwise, the request triggers a `SECURITY BREACH` and the streaming block breaks connection.
- **Explicit Chat Feedback:** When any firewall filter is enabled, the chat endpoint injects human-readable telemetry into the response. A blocked query returns `[FW_BLOCK] Segment violation` with the exact metric that triggered the breach. A passed query prepends `[FIREWALL_AUDIT]` followed by `[FW_PASS]` with resonance/threshold and cosine values before routing to the LLM stream. All telemetry uses language-neutral technical terms.

### 1.4 Telemetry Standards
All telemetry and logs must use structured ASCII headers (e.g., [FIREWALL_AUDIT], [FW_BLOCK], [FW_PASS]) and the multi-line `Metric | Limit` format.
Emojis are strictly prohibited in backend-generated strings.
The AuditPanel is deprecated in favor of the Sniffer's Full Payload Interception (FPI). Sniffer history is now volatile via API.

## 2. Backend Architecture
Utilizes **FastAPI** for route management yielding high execution throughput. The backend follows a **layered separation of concerns**:

```
app/
├── core/                    # Framework-agnostic logic
│   ├── models.py            # Pydantic models (ConfigState, ConfigUpdate, etc.)
│   ├── state.py             # Global config singleton + asyncio.Lock + set_config()
│   ├── firewall.py          # SemanticFirewall engine (pure vector math) + ClauseResult TypedDict
│   └── settings.py          # Environment-driven settings (Ollama, embedder, chunks)
├── api/
│   ├── router_main.py       # Entry point — includes all sub-routers
│   └── endpoints/
│       ├── _shared.py       # verify_api_key + limiter (shared across endpoints)
│       ├── corpus.py        # PDF upload, task status, packs, deletion
│       ├── config.py        # /galaxy/config (GET+POST), profiles, /audit
│       ├── chat.py          # /chat and /v1/chat/completions (unified provider)
│       └── system.py        # /health, /system/stats, /v1/sniffer/stream
└── modules/
    ├── embedder.py          # BGE-M3 embedding singleton
    ├── storage.py           # LanceDB vector store
    ├── ingestor.py          # PDF chunking pipeline + TaskStore with TTL
    ├── sniffer.py           # RTSS producer-consumer + SSE + persistence
    ├── profiles.py          # JSON profiles with path traversal protection
    └── providers/           # Strategy pattern for LLM backends
        ├── base.py
        ├── ollama.py
        ├── google.py
        ├── openai.py
        ├── anthropic.py
        └── groq.py
```

- **Firewall Engine (`core/firewall.py`):** `SemanticFirewall` class with static methods — completely agnostic of web framework, embedders, and storage. Receives numpy arrays and a frozen `ConfigState`, returns structured `ClauseResult` (TypedDict). Portable for CLI tools, batch audits, or alternative API wrappers. Contains: `segment()`, `run_noise_filter()`, `run_cosine_filter()`, `run_excitation_filter()`, `build_pipeline()`, `evaluate_clause()`.
- **Models (`core/models.py`):** All Pydantic schemas. `ConfigState` is a **frozen BaseModel** — immutable after construction. `Field` constraints enforce value ranges. `@model_validator` ensures pipeline order uniqueness.
- **State (`core/state.py`):** Configuration singleton + `asyncio.Lock` for serialized writes. `set_config()` is an **async** function that acquires the lock before performing merge-validate-swap, guaranteeing no concurrent config corruption. A separate `set_config_sync()` exists for single-threaded test harnesses only. Each request handler snapshots the reference at entry (`cfg = config_state`) for mid-request consistency.
- **Routes (`api/router_main.py` + `api/endpoints/`):** Decomposed into thematic sub-routers (corpus, config, chat, system) aggregated by `router_main.py`. Each endpoint module imports shared dependencies (`verify_api_key`, `limiter`) from `_shared.py`. The `/chat` endpoint uses `BaseProvider.stream_chat()` (no standalone `stream_ollama` function). Providers are instantiated lazily inside request handlers to prevent boot-time crashes if API keys are missing.
- **Embedder Singleton (`modules/embedder.py`):** Automatically maps Tensor operations sequentially to Apple Silicon (`MPS`), Nvidia (`CUDA`), or fallback CPU. The model name is read from the `settings` singleton.
- **Storage Layer (`modules/storage.py`):** Serverless **LanceDB** vector store ensuring BigInt capacity on IDs natively structured via `LanceModel` (id, vector, text, metadata). Implements native JSON metadata grouping for dynamic **Document Management** (`get_summary`, `delete_pack`) allowing live corpus curation. Filename validation prevents SQL injection on delete operations.
- **Ingestor Protocol (`modules/ingestor.py`):** Employs `PyMuPDF` iteratively with Python `asyncio.to_thread` for non-blocking chunking routines. Chunk size, overlap, and batch size are read from the `settings` singleton (defaults: 512, 50, 10). Completed/failed tasks are automatically pruned after 1 hour (`TaskStore` with TTL). Updated default chunking parameters for higher granularity: chunk_size=512, chunk_overlap=50. This ensures that specific adversarial instructions are not "diluted" within large text blocks, increasing the signal-to-noise ratio for the Variance filter.
- **Settings (`core/settings.py`):** Uses `pydantic-settings` (`BaseSettings`) for typed, validated configuration following 12-Factor App principles. All env vars are declared in a single `Settings` class with type annotations, default values, and range constraints. The `.env` file is loaded automatically at boot — no `source` or manual export required. If a variable has an invalid type or fails validation, the app crashes immediately with a clear Pydantic error (fail-fast). Secrets (`FIREWALL_API_KEY`) use `SecretStr` to prevent accidental logging. A singleton `settings` instance is created at import time and imported by all modules. The backend and frontend share a single root-level `.env` file — see `.env.example` for the full list. Vite reads the same file via `envDir: '..'` in `vite.config.ts`.

## 3. Execution Pipeline (Sequential Reorderable Firewall)
The firewall executes three distinct validation stages in a **user-defined sequence** controlled via the HUD's `Seq` inputs. The pipeline is constructed at evaluation time by sorting the three stages based on their integer priority values:

| Stage | Filter | Config Key | Default Order |
|-------|--------|------------|---------------|
| A | **Noise Pre-Filter** | `noise_order` | 1 |
| B | **Cosine Filter** | `cosine_order` | 2 |
| C | **Excitation Filter** | `excitation_order` | 3 |

**Stage A — Noise Pre-Filter (Entropy Analysis):** Replaces Variance analysis. Computes the Shannon Entropy of the Query Vector ($Q$) to detect GCG (Greedy Coordinate Gradient) artifacts. Math: $H(Q) = -\sum p_i \log_2(p_i)$, where $p_i$ is the normalized distribution of the 1024D embedding (L1-normalized absolute values). Natural language embeddings exhibit high entropy (distributed information). Adversarial "bursts" (e.g., "! ! ! !") collapse the embedding into low-entropy clusters. If $H(Q) < global\_noise\_limit$ (Default: 4.5), the query is blocked as a `Burst Detection Breach`. This is corpus-independent — the filter does not require a context vector.

**Stage B — Cosine Filter:** Traditional cosine similarity gate. Computes `cos(Q, C) = dot(Q, C) / (‖Q‖ × ‖C‖)` using **raw vectors** (no normalization). Includes zero-norm guard and `np.clip(raw, -1.0, 1.0)` for floating-point safety. Blocks if `cos(Q, C) < cosine_threshold`.

**Stage C — Excitation Filter:** Dimensional resonance count. For each of 1024 dimensions, counts activations where `|Q_i - C_i| <= noise_tolerance`. Uses **raw vectors**. Applies the adaptive threshold (see Section 4). Blocks if `activations < threshold`.

**Execution semantics:** Stages are sorted by their `_order` integer (ascending). If Stage N returns BREACH, Stages N+1..3 are **never evaluated**. Each clause from the segmentation defense (Section 5) must independently pass the **entire** ordered pipeline. Telemetry trace format: `Pipeline: [cosine:OK → excitation:OK → noise:OK]` or `[cosine:OK → excitation:BREACH]`.

### 3.1 Firewall Mode: Positive / Negative (Allowlist vs Denylist)

The pipeline supports two operating modes controlled by `firewall_mode` (default: `"positive"`), togglable at runtime via the HUD or `POST /galaxy/config`.

**Positive mode (allowlist):** The current default. Queries must be semantically aligned with the corpus to pass. Each filter checks for similarity — the first filter that detects divergence triggers an immediate BREACH.

| Filter says | Effective decision | Action |
|---|---|---|
| Similar (raw pass) | **OK** | Continue to next filter |
| Not similar (raw fail) | **BREACH** | Short-circuit, block prompt |
| All filters OK | **PASS** | Route to LLM |

**Negative mode (denylist):** The corpus defines restricted content. Queries must NOT be similar. The raw filter result is inverted via `effective_passed = not raw_passed`. The first filter that detects similarity triggers an immediate BREACH.

| Filter says | Effective decision | Action |
|---|---|---|
| Similar (raw pass) | **BREACH** | Short-circuit, block prompt |
| Not similar (raw fail) | **OK** | Continue to next filter |
| All filters OK (all diverged) | **PASS** | Route to LLM |

**Symmetric short-circuit:** Both modes use the same early-exit logic — only the interpretation of the raw filter result changes. The trace records `effective_passed` (mode-aware), not the raw result, so the pipeline trace always reads `OK`/`BREACH` in context.

**No-context handling:** When the corpus returns zero results for a clause:
- **Positive:** BREACH — cannot verify alignment.
- **Negative:** PASS — no restricted content to match against.

**Breach reason prefix:** In negative mode, `breach_reason` is prefixed with `negative:` (e.g. `"negative:cosine"`) to distinguish from positive-mode breaches in telemetry and sniffer traces.

## 4. Adaptive Clause Logic (Polarity Inversion)
When the hybrid segmentation engine (Section 6.1) splits a prompt into clauses, short clauses receive a logic-inverted threshold multiplier based on mode.

- **Config:** `adaptive_factor` (float, default 0.85, range 0.01–1.00). User-adjustable via HUD slider.
- **Rule:** If a clause contains **fewer than 6 words**, logic inversion applies:
  - **Positive Mode:** `threshold = excitation_threshold * adaptive_factor` (Default 0.85x). Provides forgiveness for short, terse queries.
  - **Negative Mode:** `threshold = excitation_threshold * (1.15)`. Increases the similarity requirement for short queries to prevent "diluted" danger signals from triggering false negatives on brief malicious prompts.
- **Scope:** This adaptive reduction applies **only** within the Excitation Filter stage of the pipeline. Cosine and Noise filters use their full thresholds regardless of clause length.
- **HUD Feedback:** The ControlPanel displays real-time dimension requirements: `Short Query Req: {threshold × factor} dims` and `Full Query Req: {threshold} dims`.
- **Telemetry:** When a short clause triggers the adaptive path, the BREACH message includes: `[ADAPTIVE] Short Clause Detected. Applying {factor}x factor.`

## 5. Frontend Control Logic
- **State Management:** Overarched by **Zustand** React 19 Store using a **4-slice architecture**: `FirewallSlice` (config, modes, pipeline orders), `ChatSlice` (messages, input state), `SystemSlice` (telemetry, ingestion, global status), `SnifferSlice` (logs, filters). Telemetry is isolated in the System slice to prevent 1Hz poll updates from re-rendering the chat message list. The exported `useStore` hook composes all slices — no consumer-facing API change.
- **HUD Telemetry (`TelemetryHUD.tsx`):** Periodically polls `/system/stats` for PSUtil & CPU / Torch RAM mappings. Uses CSS classes from `styles/ControlPanel.css` (extracted from inline styles). Displays **Three Monkey Heads** (one per filter: Noise, Cosine, Excitation) — each head animates when its filter is enabled and goes dark when disabled, providing visual pipeline status. Also shows the current `systemAction` state and a compact telemetry line (CPU/RAM/GPU). On Apple Silicon (MPS), GPU% is calculated as `torch.mps.current_allocated_memory() / psutil.virtual_memory().total * 100` — reflecting actual allocation against total unified memory. On CUDA, it uses `torch.cuda.memory_allocated() / torch.cuda.get_device_properties(0).total_mem * 100`.
- **Pipeline Ordering UI (`ControlPanel.tsx`):** Uses CSS classes from `styles/ControlPanel.css` (inline styles extracted). Slider groups are visually ordered to match the default pipeline execution sequence: **Noise Pre-Filter (Seq 1)** → **Cosine Gate (Seq 2)** → **Excitation Threshold + Noise Tolerance (Seq 3)** → **Adaptive Factor**. On mount, `ControlPanel` fetches `GET /galaxy/config` to hydrate the Zustand store with actual backend state — eliminating default value desync (e.g. `globalNoiseLimit: 0.50` vs `4.5`). Each filter includes a **Seq** numerical input (1–3) that controls pipeline execution order and an **ON/OFF toggle button** that enables or disables that individual filter. When a filter is toggled OFF, its slider group dims via `.filter-group--disabled` class and the filter is excluded from the pipeline entirely (via `build_pipeline()` in the engine). The firewall is considered active when at least one filter is enabled (`fw_on = noise_enabled || cosine_enabled || excitation_enabled`). There is no user-prompt bypass — the firewall can only be disabled via the authenticated HUD toggles. All values including enabled states are synced to the backend via debounced `POST /galaxy/config`.
- **Interface Guardrails (`ChatInterface.tsx`):** Uses `crypto.randomUUID()` for collision-free message IDs. Decodes raw NDJSON via `aiter_lines()` from the backend to guarantee seamless UTF-8 character stability for multi-byte accents organically. Each component is wrapped in an `ErrorBoundary` to prevent cascading UI crashes — a single panel failure renders a retry button instead of killing the entire app.
- **Centralized API Config (`config.ts`):** All API calls reference `API_BASE_URL` from `import.meta.env.VITE_API_BASE_URL` (default: `http://localhost:8000`). Zero hardcoded URLs in components.
- **I18n Tooltip Architecture:** Implements a decoupled string registry for UI telemetry and guidance.
  - **Structure:** Tooltips are stored in `src/locales/tooltips.ts` as a structured object, allowing for runtime language switching.
  - **Content:** Each entry includes title, description, mechanics, and suggested (mode-aware).

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

### 6.3 Configurable RAG Context Depth (Top-K)
The number of corpus chunks retrieved **per clause** for RAG context is controlled by `rag_top_k` (default 12, range 1–32). Configurable via:
- **Environment variable:** `RAG_TOP_K` in `.env` (boot-time default for settings; runtime uses `ConfigState`).
- **Runtime HUD:** "RAG Context Depth" slider in the ControlPanel (synced via `POST /galaxy/config`).

For each clause that has LanceDB hits, the `chat_endpoint` retrieves the top-K nearest chunks and **unions** their texts across all clauses (deduplicated by chunk `id`, first-seen order), joined with `\n---\n`. The firewall evaluation still runs against the **top-1 nearest vector only** — additional chunks affect LLM quality but not security math. PASS telemetry reports `RAG: N chunks injected (k=…, clauses=…, unique=…)`. The `audit_query` endpoint returns the joined `context` and `rag_chunk_count` for consistency.

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
Backend dependencies are managed by `uv`. The source of truth is `backend/pyproject.toml` (the `[project]` table) with the exact resolved set locked in `backend/uv.lock`; pins target exact versions (e.g. `fastapi==0.135.1`). `requirements.txt` is retained only as a generated artifact (`uv pip compile pyproject.toml -o requirements.txt`) for consumers that cannot use `uv`, and must not be hand-edited. Exact pinning prevents silent breakage from upstream updates — particularly critical for `sentence-transformers` and `torch`, where version changes can alter embedding output and invalidate the entire corpus index. Target runtime: Python >= 3.14.

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

## 9. Transparent Proxy Architecture (OpenAI V1 Spec)
To ensure zero-friction integration, the firewall exposes a `/v1/chat/completions` endpoint.
- **Provider Pattern:** Logic is abstracted into `app/modules/providers/`. The `BaseProvider` defines the interface for `stream_chat`. Initial implementation: `OllamaProvider`.
- **Interception Logic:** The proxy extracts the *last* message from the `messages` array. This message is passed through the `SemanticFirewall` segmentation and evaluation pipeline.
- **Error Handling:** If a `SECURITY BREACH` occurs, the proxy returns a 403 Forbidden response using the OpenAI standard error format: `{"error": {"message": "...", "type": "security_breach", "code": "403"}}`.
- **Upstream Errors in Streams:** To prevent silent stream failures or "empty chunk" responses if an upstream provider (e.g., Google or Ollama) fails mid-process or throws an HTTP initialization error (like a 404 for deprecated models like `gemini-1.5`), the `BaseProvider` implementation catches any HTTP non-200 responses and yields a native Server-Sent Events chunk embedding the error. This error (`🔴 [LLM ERROR] ...`) cascades properly through the streaming architecture straight to the frontend sniffer or client UI without breaking the HTTP header phase.
- **Streaming:** Implements Server-Sent Events (SSE) via `httpx`. TTFT (Time To First Token) is optimized for Apple Silicon (MPS) by maintaining the embedding model in unified memory.

### 9.1 Google Gemini Provider
Implements the BaseProvider interface for Google's Generative AI API.
- **Endpoint:** `v1beta/models/{model}:streamGenerateContent?alt=sse`.
- **Normalization:** Maps Gemini's `candidates[0].content.parts[0].text` structure into the OpenAI-compatible `choices[0].delta.content` SSE format.
- **Security:** Requires `GOOGLE_API_KEY`. The key is sent via the `x-goog-api-key` HTTP header (not as a URL query parameter) to prevent leakage in access logs, proxies, and CDN caches. The system performs a fail-fast check at request time; if `UPSTREAM_PROVIDER` is set to `google` and the key is missing, the provider factory raises a `RuntimeError`.

### 9.2 OpenAI Provider
Implements the BaseProvider interface for the official OpenAI API.
- **Endpoint:** `https://api.openai.com/v1/chat/completions`.
- **Security:** Requires `OPENAI_API_KEY`. The key is sent via the `Authorization: Bearer` header. The system performs a fail-fast check at request time.

### 9.3 Anthropic Provider
Implements the BaseProvider interface for the Anthropic API.
- **Endpoint:** `https://api.anthropic.com/v1/messages`.
- **Normalization:** Maps Anthropic's `content_block_delta` structure into the OpenAI-compatible `choices[0].delta.content` SSE format. Extracts the top-level `system` message from the array.
- **Security:** Requires `ANTHROPIC_API_KEY`. The key is sent via the `x-api-key` header. The system performs a fail-fast check at request time.

### 9.4 Groq Provider
Implements the BaseProvider interface for the Groq API (OpenAI-compatible).
- **Endpoint:** `https://api.groq.com/openai/v1/chat/completions`.
- **Security:** Requires `GROQ_API_KEY`. The key is sent via the `Authorization: Bearer` header. The system performs a fail-fast check at request time.

### 9.5 Provider Factory
The `chat_endpoint` and `openai_proxy` resolve the provider lazily at request time via `get_provider(cfg: ConfigState) -> tuple[BaseProvider, str]`. This returns a tuple of the provider instance and the model ID from settings based on the `UPSTREAM_PROVIDER` environment variable. Lazy instantiation means a missing Google API key does not crash the app at import time — it only fails when the `/chat` or proxy endpoint is actually called. This ensures the Semantic Firewall remains provider-agnostic and the system prompt for context-confined operation is injected at the endpoint level (prepended to the messages array) before calling `provider.stream_chat()`.

## 10. Real-Time Semantic Sniffer (RTSS)
A zero-latency observability layer for the OpenAI V1 Proxy (`/v1/chat/completions`). Captures every firewall decision and LLM response preview without introducing latency to the primary inference stream.

### 10.1 Producer-Consumer Decoupling
- **Pattern:** `asyncio.Queue(maxsize=256)` with fire-and-forget `put_nowait()`.
- **Producer:** `emit_trace()` is called synchronously from the proxy endpoint on both BREACH and PASS paths. The proxy stream never awaits sniffer persistence. `emit_trace()` is mandatory for all terminal firewall decisions (PASS/BREACH) across both `/chat` and `/v1/chat/completions` endpoints to ensure forensic parity in the RTSS.
- **Consumer:** A background `asyncio.Task` (spawned at startup via `asyncio.create_task()` inside the FastAPI lifespan, cancelled at shutdown) reads from the queue, appends to a circular buffer (max 100 entries), and broadcasts to all SSE subscribers.
- **Task Spawning:** `start_consumer()` uses `asyncio.create_task()` — the modern Python 3.10+ API. This avoids the `DeprecationWarning` emitted by `asyncio.get_event_loop()` when no running loop is present. It is always called from within the async lifespan context where a loop is guaranteed to exist.

### 10.2 SnifferTrace Schema
```typescript
interface SnifferTrace {
  id: string;               // UUID v4
  timestamp: string;        // ISO 8601 UTC
  request: {
    model: string;
    last_message: string;   // First 200 chars of the intercepted message
  };
  firewall: {
    decision: "PASS" | "BREACH";
    pipeline_trace: Array<{
      stage: "noise" | "cosine" | "excitation";
      passed: boolean;
      value: number;         // Actual metric (avg_delta, cosine_sim, activations)
      threshold: number;     // Configured threshold for this stage
    }>;
  };
  response_preview: string;  // First 100 chars of LLM response
}
```

### 10.3 SSE Transport
- **Endpoint:** `GET /v1/sniffer/stream` (protected by API key when configured).
- **Protocol:** Server-Sent Events — unidirectional, lighter than WebSockets, native reconnection.
- **Subscriber pattern:** Each connected client receives its own `asyncio.Queue`. A 30-second heartbeat (`: heartbeat\n\n`) prevents proxy/browser timeouts.
- **Module:** `app/modules/sniffer.py` — contains `SnifferTrace` model, queue, `emit_trace()`, consumer task, subscriber management, and SSE generator.
- **Thread-Safety Contract:** `_trace_buffer` (circular buffer, max 100 entries) is accessed exclusively from the asyncio event loop. The consumer task, `update_trace()`, and `stream_sniffer_sse()` all execute in the same loop under cooperative scheduling — no lock is required. If a threaded consumer is introduced in the future, an `asyncio.Lock` must protect all buffer access.

### 10.4 Frontend Integration
- **Component:** `SnifferTab.tsx` — rendered as a new tab in `App.tsx` (Chat | Sniffer).
- **Constraint:** Does NOT modify `ChatInterface.tsx` or `ControlPanel.tsx`.
- **State:** Uses the Zustand store for the sniffer log buffer (max 100 entries) and filter state.
- **Filtering:** Dropdowns for decision (ALL/PASS/BREACH) and stage (ALL/Noise/Cosine/Excitation).
- **Display:** Color-coded log entries with pipeline stage badges, timestamps, model names, and response previews. New entries animate in with a fade-slide.
- **Expandable Rows:** Click any trace entry to expand an inline detail panel showing the full request history (formatted JSON) and reconstructed LLM response. Status badges show `PENDING` (pulsing amber), `COMPLETED` (green), or `BREACH` (red).

### 10.5 Full Payload Interception (FPI)
Evolves the RTSS from a firewall-decision-only observer into a full I/O capture system.

**Input Capture:** The proxy captures the **entire** `config.messages` array (all roles: system, user, assistant) — not just the last message. This is stored as `request_history` in the `SnifferTrace`, giving forensic visibility into multi-turn conversation context.

**Output Reconstruction:** An async `stream_wrapper` generator wraps `provider.stream_chat()`. It intercepts each SSE chunk, extracts `choices[0].delta.content`, and appends it to a local buffer — all without blocking the `yield` to the client. When the stream terminates, the reconstructed response is committed to the trace via `update_trace()`.

**Zero-Latency Guarantee:** The wrapper is a pure pass-through: every chunk is yielded immediately after (not before) buffering. The post-stream `update_trace()` uses fire-and-forget `put_nowait()` — the client connection is already closed by the time the update fires.

**Error Propagation:** Upstream LLM exceptions (e.g. `httpx.ConnectError`, Ollama 500) are caught during generator consumption. The trace `status` is updated to `ERROR` and the exception string is committed as the `response_content` with a `🔴 [LLM_ERROR]` prefix, ensuring the frontend accurately reflects provider failures instead of silent "False OKs".

### 10.6 Stage Semantics: `no_context` & `noise`
`no_context` is a valid `PipelineStageTrace.stage` value alongside `noise`, `cosine`, and `excitation`. It is emitted when the corpus returns zero results for a clause — the firewall cannot evaluate dimensional alignment because there is no reference vector to compare against.
The noise stage now explicitly reports Shannon Entropy as its primary metric in the SnifferTrace.

- **`value`:** `0.0` — no metric was computed (corpus miss, not a threshold failure).
- **`threshold`:** `0.0` — no threshold applies.
- **`passed`:** `false` — the clause is blocked; an empty corpus is treated as a security breach.

Frontend consumers should render `no_context` as a **corpus miss** indicator rather than a threshold comparison bar. The stage is handled as an explicit branch in `emit_trace()` to prevent it from silently falling through to the generic default case.

### 10.7 Trace Correlation
Each PASS trace is assigned a UUID `trace_id` at emit time. This ID correlates the initial request capture (emitted before streaming begins) with the final response reconstruction (committed after the stream terminates). BREACH traces are self-contained — they receive `status="BREACH"` immediately since no streaming occurs.

`update_trace()` scans the circular buffer for the matching `trace_id`, rebuilds the frozen Pydantic model with `response_content` and `status="COMPLETED"`, and pushes the updated trace through the sniffer queue so SSE subscribers receive the completed payload.

### 10.8 SnifferTrace Schema v2
```typescript
interface SnifferTrace {
  id: string;               // UUID v4 (trace_id for correlation)
  timestamp: string;        // ISO 8601 UTC
  request: {
    model: string;
    last_message: string;   // First 200 chars (backward compat)
    request_history: Array<{role: string; content: string}>;  // Full messages array
  };
  firewall: {
    decision: "PASS" | "BREACH";
    pipeline_trace: Array<{
      stage: "noise" | "cosine" | "excitation";
      passed: boolean;
      value: number;
      threshold: number;
    }>;
  };
  response_preview: string;  // First 100 chars of LLM response
  response_content: string;  // Full reconstructed response (FPI) or error message
  status: "PENDING" | "COMPLETED" | "BREACH" | "ERROR";
}
```

---

## 11. Configuration Profiles & Persistence

### 11.1 Overview

The SSA (Session State Architecture) protocol provides persistent configuration across restarts through orthogonal mechanisms:

1. **Config Profiles** — named JSON snapshots of `ConfigState` stored in `backend/data/`
2. **Sniffer History** — circular trace buffer flushed to `backend/data/sniffer_history.json`
3. **Chat Persistence** — Last 100 messages flushed to `backend/data/chat_history.json` and synchronized with Zustand (`firewall-chat-storage`).
4. **Active Tab Persistence** — last UI tab stored as `active_tab` inside `ConfigState` and carried forward via `_last_used`

### 11.2 ProfileManager (`backend/app/modules/profiles.py`)

```
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
```

The `DATA_DIR` is resolved as an absolute path relative to the module file — guaranteeing the same location regardless of process working directory (pytest, uvicorn, or CLI).

| Method | Behaviour |
|---|---|
| `save_profile(name, state)` | Validates name against `_SAFE_PROFILE_RE`, then serializes `ConfigState` → `{name}.json` via `model_dump_json()` |
| `load_profile(name)` | Validates name, returns a `dict` or `None` if not found. Catches all parse errors. |
| `list_profiles()` | Returns sorted list of stems; underscore-prefixed profiles excluded. |
| `delete_profile(name)` | Validates name. Rejects underscore-prefixed names. Returns `True` if deleted. |

**Path Traversal Protection (Audit Finding S3):** A `_SAFE_PROFILE_RE` regex (`^[a-zA-Z0-9_\-]{1,64}$`) is enforced on all public methods via `_validate_name()`. This prevents names like `../../etc/passwd` from escaping `DATA_DIR`. All profile names are restricted to alphanumeric characters, underscores, and hyphens (max 64 chars).

**Naming convention:** underscore prefix (`_`) = internal/protected (e.g., `_last_used`, `_default`). These never appear in the public listing and cannot be deleted via `delete_profile()`.

### 11.3 Auto-Persistence on Config Change

Every call to `POST /galaxy/config` atomically:
1. Updates `config_state` under `asyncio.Lock` (existing behaviour).
2. Calls `ProfileManager.save_profile("_last_used", new_state)` — fire-and-forget, synchronous (no lock contention; writes are fast JSON).

### 11.4 Auto-Load at Startup (`core/state.py`)

At module load time (before the first request), `state.py` calls `_load_initial_state()`:

```python
data = ProfileManager.load_profile("_last_used")
if data:
    return ConfigState(**data)
return ConfigState()   # factory defaults
```

If `_last_used.json` is absent, malformed, or fails Pydantic validation, the module falls back to `ConfigState()` defaults with a warning log. **No crash, no data loss.**

### 11.5 Profile API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/galaxy/config` | Return current config state (frontend hydration) |
| `POST` | `/galaxy/config` | Update firewall config (with auto-calibration) |
| `GET` | `/galaxy/profiles` | List user-visible profiles |
| `POST` | `/galaxy/profiles/save/{name}` | Save current config as `{name}` |
| `POST` | `/galaxy/profiles/load/{name}` | Load `{name}` and apply as active config |
| `DELETE` | `/galaxy/profiles/{name}` | Delete `{name}` (protected names: 404/error) |

All endpoints require `X-API-Key` if `FIREWALL_API_KEY` is set.

Loading a profile auto-saves it as `_last_used` so the next restart restores the loaded profile.

### 11.6 active_tab Field

`ConfigState` (and `ConfigUpdate`) now carry an `active_tab: str` field (default `"chat"`).

The frontend writes `active_tab` into every config sync debounce payload. On next session load, `_load_initial_state()` restores the last active tab, and the frontend can use it to restore tab position without additional API calls.

### 11.7 Sniffer Persistence Layer

The RTSS circular buffer is flushed to `backend/data/sniffer_history.json` on every trace processed by `sniffer_consumer()`.

**At consumer startup (`sniffer_consumer()`):**
```python
_trace_buffer = _load_history_sync()  # up to _BUFFER_MAX=1000 entries
```

**On every trace (new or updated):**
```python
snapshot = list(_trace_buffer)
asyncio.create_task(asyncio.to_thread(_save_history_sync, snapshot))
```

`asyncio.to_thread()` offloads the blocking file write to a thread pool without blocking the event loop. The `snapshot` is a shallow copy taken before the async hand-off to prevent race conditions.

**_BUFFER_MAX = 1000** (increased from 100) — the in-memory circular buffer and the JSON history file are capped at 1000 entries. Oldest entries are evicted FIFO when the cap is reached.

**Resilience:** `_load_history_sync()` catches all `json.JSONDecodeError` and generic exceptions, returning `[]` on failure. The consumer continues normally even if history is corrupted.

### 11.7.5 Chat Persistence (Hybrid Architecture)
The chat endpoint triggers a background save to `backend/data/chat_history.json` (max 100 entries) on every successful LLM generation round. All file I/O operations for `chat_history.json` are wrapped with a `threading.RLock` that covers the entire Read-Modify-Write cycle. This guarantees reentrant atomic transactions and thread-safety during concurrent accesses, eliminating race conditions. The RLock protects all entry points to chat history (CRUD + Atomic).
On the frontend, `App.tsx` hydrates the Zustand store on mount by polling `GET /chat/history`, seamlessly merging with the `persist` middleware `firewall-chat-storage`.

### 11.8 Data Directory Layout

```
backend/
├── data/
│   ├── _last_used.json          # Auto-saved on every config change
│   ├── sniffer_history.json     # RTSS buffer — last 1000 traces
│   ├── chat_history.json        # Unified chat message persistence (max 100)
│   └── <name>.json              # User-saved config profiles (created via the API)
└── logs/
    └── firewall.log[.YYYY-MM-DD] # Rotating daily logs, 30-day retention
```

All of the above are **runtime-generated and untracked**: `backend/data/*.json` and `backend/logs/` are excluded from version control via the root `.gitignore`, so no intercepted prompts, responses, chat history, or logs ever enter git. The `data/` directory is created at import time by `DATA_DIR.mkdir(exist_ok=True)` in both `profiles.py` and `sniffer.py`; config profiles are written on demand by `ProfileManager`, not shipped with the repo.

### 11.9 Mode-Aware Auto-Calibration (Non-Intrusive)

The `update_config` logic enforces Phase 2.1 optimized constants when `firewall_mode` is toggled, but **respects user intent** on a per-field basis:

| Mode | `cosine_threshold` | `excitation_threshold` | `global_noise_limit` |
|---|---|---|---|
| **Positive** | 0.5315 | 150 | 4.5 |
| **Negative** | 0.6197 | 170 | 4.5 |

**Non-Intrusive Logic:** For each threshold field (`cosine_threshold`, `excitation_threshold`), the system checks whether the request value differs from the current state. If the user explicitly changed a value (slider moved), that value is preserved. Smart defaults are applied **only** to fields the user did not touch during the mode toggle.

**Profile Sovereignty:** `POST /galaxy/profiles/load/{name}` bypasses auto-calibration entirely — profiles are loaded exactly as saved, with no constant overrides.

Calibration is **atomic** — it occurs inside the `asyncio.Lock` during `POST /galaxy/config`. Constants are only applied when the mode actually **changes** (same-mode config updates preserve all user values). The response returns `new_state.model_dump()` so the frontend HUD reflects the adjusted values immediately.

### 11.10 Visibility Mapping
The `_last_used` profile is now exposed to the frontend via `list_profiles()` but aliased as "🕒 Last Session (Auto-save)" to provide user feedback on persistence.

### 11.11 One-Click Calibration
A "Reset to Recommended" function applies mode-aware Youden constants (Positive: 0.5315/150; Negative: 0.6197/170) to ensure optimal F1-score performance without manual slider hunting.

## 12. Industrial Logging & Forensics

### 12.1 Rotating File Handler
Implements `logging.handlers.TimedRotatingFileHandler`. Logs are rotated daily at midnight.

### 12.2 Retention Policy
30-day retention window. Total log volume capped by filesystem limits (recommended 100GB).

### 12.3 Forensic Export
`GET /system/logs/export` aggregates in-memory sniffer traces and chat history into a portable JSON forensic package for audit purposes.
