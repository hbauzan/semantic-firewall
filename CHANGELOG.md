# Changelog

Notable capabilities and releases. Append only on releases or meaningful capability changes — not on every micro-fix.

The previous `manifest.json` `active_features` ledger (per-flag historical trail) was retired in favor of this file and a slim manifest (`project`, `version`, `state_schema`, `constraints`).

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
