# Phase-Lock Semantic Firewall Architecture Specification

## 1. Dimensional Excitation Firewall (FED Math)
The firewall operates by evaluating the raw 1024D embedding layers produced by `BAAI/bge-m3` between a given Query Vector (`Q`) and a Context Vector from the nearest knowledge entry (`C`).
- **Delta Calculation:** For each dimension `i`, we compute the absolute delta `Delta_i = abs(Q_i - C_i)`.
- **Activation Logic:** An activation register is tripped if `Delta_i` is less than or equal to the `Noise Tolerance` configuration (default 0.005). Thus, `Activation_i = 1`.
- **Gate:** The final dimension sum `sum(Activation_i)` must be mathematically greater than or equal to the `Excitation Threshold` (default 150) to be deemed geometrically 'SAFE'. Otherwise, the request triggers a `SECURITY BREACH` and the streaming block breaks connection.
- **Explicit Chat Feedback:** When `[FW=ON]` is active, the chat endpoint injects human-readable telemetry into the response. A blocked query returns `🛑 [FW] Segment violation` with the exact metric that triggered the breach. A passed query prepends `🟢 [FW PASS]` with resonance/threshold and cosine values before routing to the LLM stream. All telemetry uses language-neutral technical terms.

## 2. Backend Architecture
Utilizes **FastAPI** for route management yielding high execution throughput.
- **Embedder Singleton (`embedder.py`):** Automatically maps Tensor operations sequentially to Apple Silicon (`MPS`), Nvidia (`CUDA`), or fallback CPU.
- **Storage Layer (`storage.py`):** Serverless **LanceDB** vector store ensuring BigInt capacity on IDs natively structured via `LanceModel` (id, vector, text, metadata). Implements native JSON metadata grouping for dynamic **Document Management** (`get_summary`, `delete_pack`) allowing live corpus curation.
- **Ingestor Protocol (`ingestor.py`):** Employs `PyMuPDF` iteratively with Python `asyncio.to_thread` for non-blocking chunking routines (size: 2048 chars, 200 overlap).

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
- **HUD Telemetry (`TelemetryHUD.tsx`):** Periodically polls `/system/stats` for PSUtil & CPU / Torch RAM mappings mapping system metrics underneath a custom ASCII-art **Pirate Monkey** multi-frame cycle. Utilizes a Mac Unified Memory dynamically-scaled heuristic (`vram / 40.0`) to avoid 100% hard-locking early.
- **Pipeline Ordering UI (`ControlPanel.tsx`):** Each filter slider (Cosine, Excitation, Noise) includes a **Seq** numerical input (1–3) that controls pipeline execution order. The `global_noise_limit` slider controls the Noise Pre-Filter threshold. All values are synced to the backend via debounced `POST /galaxy/config`.
- **Interface Guardrails (`ChatInterface.tsx`):** Implements **BigInt Safety** explicitly casting all interaction `Date.now()` iterations recursively. Decodes raw NDJSON via `aiter_lines()` from the backend to guarantee seamless UTF-8 character stability for multi-byte accents organically.

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
