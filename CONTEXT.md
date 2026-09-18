# CONTEXT — Domain Glossary

> Ubiquitous language for the Three-Headed Semantic Firewall. Definitions are tight: they say what a concept **is**, not how it is implemented. For low-level design see [`architecture_spec.md`](./architecture_spec.md); for current version and config contract see [`manifest.json`](./manifest.json); for notable releases see [`CHANGELOG.md`](./CHANGELOG.md).
>
> _Not to be confused with_ `context.txt` — a generated full-source bundle produced by `run_pack.sh` for sharing the codebase with an AI. It is git-ignored and is not part of the domain model.

---

## Core system

**Semantic Firewall** — A gate in front of an LLM that admits or rejects a prompt based on the **geometric** position of its **embedding** relative to a **corpus**, rather than on string matching or harm classification.

**Geometric Containment** — The discipline the firewall performs: bounding an LLM's effective input to a region of embedding space. Distinct from dialogue rules or harm-category classifiers.
- _Avoid_: "lobotomy" (narrative metaphor only), "content moderation".

**Corpus** — The set of trusted documents whose **embeddings** define the region of semantic space the firewall reasons about. In **positive mode** it is the allowlist; in **negative mode** it is the denylist.
- _Avoid_: "galaxy" (metaphor; also the API namespace `/galaxy/*`), "knowledge base".

**Embedding** — The 1024-dimensional vector produced by the **Embedder** for a piece of text. The space in which all firewall geometry is measured.

**Embedder** — The model that produces **embeddings** (`BAAI/bge-m3`, 1024D). Single shared instance; dense + optional sparse lexical weights via SentenceTransformer.

**Sparse lexical weights** — BGE-M3 sparse retrieval signal stored per corpus chunk (`sparse_lexical`) and compared at query time for hybrid scoring.

**RaBitQ signature** — 1024-bit binary projection of a dense vector used for Hamming pre-filtering in LanceDB search.

**Pack** — One uploaded source document ingested into the **Corpus**, tracked with a chunk count.

---

## Evaluation pipeline

**Clause** — A prompt fragment produced by **Segmentation**. The unit the **Pipeline** evaluates; a prompt passes only if every clause passes.

**Segmentation** — Splitting a prompt into **Clauses** on punctuation, force-chunking clauses over 20 words. The basis of the anti-piggybacking defense.

**Pipeline** — The ordered sequence of the three **Filters** applied to each **Clause**. Order is user-configurable; the first failing filter short-circuits.

**Filter** — One geometric test in the **Pipeline**. There are exactly three: **Noise Pre-Filter**, **Cosine Filter**, **Excitation Filter**. Each can be toggled on/off independently.

**Noise Pre-Filter** — The **Filter** that rejects a **Clause** whose global delta / Shannon entropy against the corpus vector exceeds the **Global Noise Limit**.

**Cosine Filter** — The **Filter** that rejects a **Clause** whose cosine similarity to the nearest corpus vector falls below the **Cosine Threshold**. Measures directional alignment.

**Excitation Filter** — The **Filter** that rejects a **Clause** whose **Activations** count falls below the **Excitation Threshold**. Measures value-by-axis alignment; the structurally distinctive test.

**Activations** — The count of dimensions where the per-axis delta `|Q_i − C_i|` is within **Noise Tolerance**. The Excitation Filter's metric.
- _Avoid_: "Resonance" (UI label for the same quantity).

**Whitening** — A lab change of basis \(Q'=(Q-\mu)\Sigma^{-1/2}\) (ZCA) fitted on corpus vectors so each axis has variance ~1. Not a production **Filter**; **Excitation** still counts raw BGE-M3 axes.

**Decision** — The terminal outcome of evaluating a prompt: **PASS** or **BREACH**.

**PASS** — Every **Clause** cleared the **Pipeline**; the request is forwarded to the **Provider**.

**BREACH** — A **Clause** failed a **Filter** (or, in positive mode, had no corpus match); the request is blocked and never reaches the **Provider**.

---

## Configuration

**Firewall Mode** — Whether the **Corpus** acts as an allowlist or a denylist. **Positive** (default): only corpus-aligned prompts pass. **Negative**: corpus-aligned prompts are blocked.

**Threshold parameters** — The tunable bounds each **Filter** compares against: **Cosine Threshold**, **Excitation Threshold**, **Global Noise Limit**, **Noise Tolerance**.

**Adaptive Factor** — A multiplier that relaxes the **Excitation Threshold** for short clauses (< 6 words).

**Auto-Calibration** — Mode-aware adjustment of **Threshold parameters** to recommended (Youden-derived) constants when **Firewall Mode** changes, without overwriting manual edits.

**Profile** — A named, saved snapshot of the full configuration state, persisted and reloadable via `ProfileManager`.

**RAG Context** — The union of up to `rag_top_k` corpus chunks **per clause** (deduplicated) attached to a **PASS**ed prompt as grounding before it reaches the **Provider**. Firewall geometry still uses the top-1 vector per clause.

---

## Providers & surfaces

**Provider** — An adapter implementing the `BaseProvider` interface (`stream_chat`) behind which every LLM lives. Implementations: Ollama (default, local), OpenAI, Anthropic, Google, Groq.
- _Avoid_: "backend" (ambiguous with the FastAPI service), "model" (a Provider may serve many models).

**Upstream** — The **Provider** the firewall forwards a **PASS**ed prompt to. An unreachable upstream yields a graceful client error, not a crash.

**Transparent Proxy** — The `POST /v1/chat/completions` surface implementing the OpenAI spec, so any OpenAI-compatible client gains firewall interception with no code change. Returns `403` on **BREACH**.

**Chat endpoint** — The `POST /chat` surface used by the built-in **HUD**; streams NDJSON with inline firewall telemetry.

---

## Observability

**RTSS (Real-Time Semantic Sniffer)** — The subsystem that captures every terminal **Decision** as a **Trace** and streams it live.

**FPI (Full Payload Interception)** — The RTSS capability of recording the full request history plus the reconstructed response on a **Trace**.

**Trace** — One audit record of a single **Decision**: timestamp, request, **Pipeline** trace (per-stage metric vs threshold), decision, and status. The auditable unit of the system.

**HUD** — The browser control surface (Telemetry HUD + Control Panel) for operating filters, thresholds, packs, and watching traces.

**Runtime fingerprint** — The recorded tuple of embedder id, library versions, device and backend that bounds a determinism claim on one machine. Distinct from a Nivel 3 registered signature.
