# Phase-Lock Semantic Firewall Architecture Specification

## 1. Dimensional Excitation Firewall (FED Math)
The firewall operates by evaluating the raw 1024D embedding layers produced by `BAAI/bge-m3` between a given Query Vector (`Q`) and a Context Vector from the nearest knowledge entry (`C`).
- **Delta Calculation:** For each dimension `i`, we compute the absolute delta `Delta_i = abs(Q_i - C_i)`.
- **Activation Logic:** An activation register is tripped if `Delta_i` is less than or equal to the `Noise Tolerance` configuration (default 0.005). Thus, `Activation_i = 1`.
- **Gate:** The final dimension sum `sum(Activation_i)` must be mathematically greater than or equal to the `Excitation Threshold` (default 150) to be deemed geometrically 'SAFE'. Otherwise, the request triggers a `SECURITY BREACH` and the streaming block breaks connection.
- **Explicit Chat Feedback:** When `[FW=ON]` is active, the chat endpoint injects human-readable telemetry into the response. A blocked query returns `🛑 [FIREWALL BLOCKED]` with the exact resonance ratio (`activations/1024`) versus the threshold. A passed query prepends `🟢 [FIREWALL PASSED]` with `activations/threshold` before routing to the LLM stream.

## 2. Backend Architecture
Utilizes **FastAPI** for route management yielding high execution throughput.
- **Embedder Singleton (`embedder.py`):** Automatically maps Tensor operations sequentially to Apple Silicon (`MPS`), Nvidia (`CUDA`), or fallback CPU.
- **Storage Layer (`storage.py`):** Serverless **LanceDB** vector store ensuring BigInt capacity on IDs natively structured via `LanceModel` (id, vector, text, metadata). Implements native JSON metadata grouping for dynamic **Document Management** (`get_summary`, `delete_pack`) allowing live corpus curation.
- **Ingestor Protocol (`ingestor.py`):** Employs `PyMuPDF` iteratively with Python `asyncio.to_thread` for non-blocking chunking routines (size: 2048 chars, 200 overlap).

## 3. Frontend Control Logic
- **State Management:** Overarched by **Zustand** React 19 Store maintaining configuration payloads, an overarching `systemAction` global state, asynchronous ingestion states, chat histories, and per-second telemetry data points.
- **HUD Telemetry (`TelemetryHUD.tsx`):** Periodically polls `/system/stats` for PSUtil & CPU / Torch RAM mappings mapping system metrics underneath a custom ASCII-art **Pirate Monkey** multi-frame cycle. Utilizes a Mac Unified Memory dynamically-scaled heuristic (`vram / 40.0`) to avoid 100% hard-locking early.
- **Interface Guardrails (`ChatInterface.tsx`):** Implements **BigInt Safety** explicitly casting all interaction `Date.now()` iterations recursively. Decodes raw NDJSON via `aiter_lines()` from the backend to guarantee seamless UTF-8 character stability for multi-byte accents organically.
