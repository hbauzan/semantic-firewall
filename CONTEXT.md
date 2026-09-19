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

**Grain** — Closed set of lab ingest units: `sentence`, `paragraph`, `section`, `document`. Not a production chunk of 512 characters.

**Pyramid** — Four-grain lineage of a pack (parent pointers + **char_span**) stored in the lab LanceDB table `knowledge_pyramid`. Production table `knowledge` stays flat.

**char_span** — Half-open `[start, end)` character offsets of a **Grain** node into the concatenated per-page source text.

**AND multi-grain** — Conjunction micro (sentence 1-NN) ∩ meso (parent paragraph) ∩ lexical (sparse overlap). No blend α. Used by compliance **Egress hold**; not an ingress **Filter**.

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

**INLP** — Lab estimate of a forbidden-theme subspace \(P\). Not a production **Filter**; not DLP of identifiers.

**Projection energy** — \(\|\Pi_P(Y)\|^2\) of an already-whitened vector \(Y\) onto \(P\).

**τ** — Cut on **Projection energy**, calibrated for 0 FPR on 100 benigns and maximum recall on 100 evasions of that theme.

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

**Egress profile** — Whether generation is released by **Sentence buffer** (`chat`) or **Egress hold** (`compliance`). Default is `chat`; CDE sets `compliance`.

**Egress hold** — Buffer of the complete generation, audited by DLP, homoglyph normalization, INLP (optional seam), reconstructed numbers, and **AND multi-grain** before any generation token reaches the client.

**Sentence buffer** — Chat-profile accumulator that freezes output on `. ; ?` or newline, then evaluates that sentence. A PAN split by newline can emit the first half; that is why **Egress hold** exists.

---

## Observability

**RTSS (Real-Time Semantic Sniffer)** — The subsystem that captures every terminal **Decision** as a **Trace** and streams it live.

**FPI (Full Payload Interception)** — The RTSS capability of recording the full request history plus the reconstructed response on a **Trace**.

**Trace** — One audit record of a single **Decision**: timestamp, request, **Pipeline** trace (per-stage metric vs threshold), decision, and status. The auditable unit of the system.

**HUD** — The browser control surface (Telemetry HUD + Control Panel) for operating filters, thresholds, packs, and watching traces.

**Runtime fingerprint** — The recorded tuple of embedder id, library versions, device and backend that bounds a determinism claim on one machine. Distinct from a Nivel 3 registered signature.

**TEI sidecar** — Optional Hugging Face Text Embeddings Inference container addressed by HTTP. The image is pinned by SHA256 digest, not a floating tag. Off by default; in-process SentenceTransformer remains the fallback.

**Oracle** — rompepepe scorer of the text **delivered** to the user. Emits block recall, FPR and egress leakage. Not an LLM-judge and not `trace.passed` from `/audit`.

**Egress leakage** — A planted secret (substring, Luhn PAN, or key regex) present in delivered text. A firewall cut message is not delivery, even if it echoes the prompt.

**Pack L01–L12** — Closed implementation wave (PRs #4–#15, 2026-09). Historical tickets/specs live under `roadmap/archivo/2026-09-pilares-l01-l12/`. Not backlog. Do not retake those IDs.

---

## Lab geometry (not production ingress)

**Oficio** — The trade the thesis locks: taller (aceite, PSI, frenos, procedimientos). Not the whole PDF.

**Lomo** — Book-spine pages that inflate min/max: radio/infoentretenimiento, legal/copyright, índice/TOC, cubiertas. A **chunk raro** is a lomo brick.

**Sobre** — Per-column floor/ceiling of ingested **oficio** rows. The useful cut is an entire row inside, not “% of dims”.

**Holgura relativa** — Slack = percent of **that** column’s observed span (`range_relative_slack`). The knob is the percent, not a global `ε`.

**z-score (lab)** — Per-column rarity vs the corpus mean/std. Another head, not a production **Filter**.

**Hoja** — All D axes of a pair: [lo, hi] of every row in each mazo. No mean. The vector is the hash.

**Δext** — On one axis, max(|Δhi|, |Δlo|) between the two painted intervals.

**Eje disjunto** — Axis whose two intervals do not overlap.

**Voto por eje** — For one coordinate against two painted intervals: `left_only` | `right_only` | `both` | `neither`. All D axes vote.

**Corte duro** — Label from the **Ejes disjuntos** only: `left` / `right` / `split` / `out`. The other axes still vote; they are not dropped.
- _Avoid_: “top-k de medias”, “las dimensiones que se mueven”.

**Sello** — Daughter tool of this repo. Paints small **almas** and decides by **Hoja** + **Corte duro**. Not a production **Filter**. Not Lxx. Pack: `roadmap/sello/`.