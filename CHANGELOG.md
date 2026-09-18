# Changelog

Notable capabilities and releases. Append only on releases or meaningful capability changes — not on every micro-fix.

The previous `manifest.json` `active_features` ledger (per-flag historical trail) was retired in favor of this file and a slim manifest (`project`, `version`, `state_schema`, `constraints`).

## Unreleased

- **Egress hold (L07):** `egress_profile=chat|compliance`. Default `chat` (live yield). `compliance` absorbs the full generation, then DLP / NFKC homoglyphs / INLP seam / reconstructed Luhn / AND multi-grain. Cut messages and sniffer/history logs never store raw PANs (`hash8:last4`). `/v1` returns 403 on egress cut.

## v2.34.0

Consolidation release & checkpoint (on pause).

### Project status & architecture research

- **Project Status Note:** Public status notice added documenting the project pause, architectural reflections on dimensional filtering, and future vision.
- **Level 2 & Bidirectional Containment Research:** Added offline research studies in `roadmap/`:
  - `cosas para estudiar - Gemini.md`: Mathematical exploration for dimensional filtering (Mahalanobis distance, Sparse Autoencoders, Matryoshka representations), multi-scale fractal chunking, high-speed Docker runtimes (Hugging Face TEI / Nomic Embed), and speculative sentence buffering for output streaming.
  - `cosas para estudiar - Cursor.md`: Conceptual boundary analysis on channel containment vs. weight lobotomy, membership testing vs. kNN similarity, and conformal prediction limitations.
- **Licensing:** Formalized project under Apache License 2.0 (`LICENSE` and `NOTICE`).
- **Metadata Alignment:** Standardized repository topics, badges, and metadata table following public project standards.

---

## v2.33.1

Current release.

### Core

- Three-filter geometric pipeline: Noise (Shannon entropy), Cosine, Excitation (per-axis activations)
- Configurable filter order and per-filter toggles
- Positive (allowlist) and negative (denylist) firewall modes
- Language-agnostic clause segmentation with overflow chunking
- Adaptive excitation threshold for short clauses
- Mode-aware auto-calibration (Youden-derived defaults without overwriting manual edits)

### Providers and surfaces

- Provider abstraction: Ollama (default, local), OpenAI, Anthropic, Google Gemini, Groq
- Transparent OpenAI-compatible proxy (`POST /v1/chat/completions`) with firewall interception
- HUD chat endpoint with NDJSON streaming and inline telemetry
- Strict RAG context on PASS (`rag_top_k`)

### RAG

- Richer per-request grounding: default `rag_top_k` 12 (range 1–32), multi-clause chunk union with deduplication, PASS telemetry reports injected chunk counts

### Operations and UI

- Real-time semantic sniffer (full payload interception, SSE, export/clear)
- Named config profiles with path-traversal protection
- Industrial rotating logs and forensic log export
- Hardware telemetry HUD
- React HUD (chat + sniffer tabs), Zustand state, i18n tooltip registry

### Tooling and security

- Backend: `uv` + `pyproject.toml` / `uv.lock`
- Frontend: `pnpm`
- Opt-in API key auth, rate limiting, security headers, CORS hardening
- Runtime data (`backend/data/*.json`), logs, and agent pack (`context.txt`) gitignored
