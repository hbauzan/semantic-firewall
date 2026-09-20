# Three-Headed Semantic Firewall — Canonical Architecture & Reactivation Roadmap

> **Standard:** IEEE 754 Full-Precision Coordinate Geometry  
> **Lineage:** Born from `semantic-firewall` v2.34.0 & `ddi-fw` RFC-003  
> **Status:** Formal Implementation Roadmap (AI-Actionable Sprints)  
> **Historical Archive:** All legacy plans and pre-v2.34.0 documents are preserved in [`roadmap/archive_v2.34.0/`](./roadmap/archive_v2.34.0/README.md).

---

## 1. Executive Summary: The Three-Headed Geometry

The **Three-Headed Semantic Firewall** is a deterministic, local-first containment gate operating on raw 1024-dimensional dense embedding vectors (produced by `BAAI/bge-m3`). It enforces strict mathematical domain boundaries before any user prompt reaches an upstream LLM.

Empirical investigations in `ddi-fw` (formalized in [RFC-003](./ddi-fw/rfc-numerical-purity-catastrophe.md)) proved that coordinate-level containment fails only when codebases commit silent decimal truncations (`round(x, 4)`, `:.4f`, float16 downcasting). Because coordinates in $\mathbb{S}^{1023}$ scale as $\mathbb{E}[|v_d|] \approx 1/\sqrt{1024} = 0.03125$ and live almost entirely within $[-0.15, +0.15]$, semantic intervals are separated by micro-gaps of $10^{-4}$ to $10^{-6}$.

When **17-digit IEEE 754 full-mantissa precision** (`%.17g`) is strictly preserved without rounding, the firewall functions as a multi-stage harmonic sieve:

```
                               Incoming Query Vector Q in R^1024
                                              │
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ HEAD 1: Cosine Difference Gate (Macro Angular Alignment)                                  │
│ - Metric: cos_sim(Q, C) >= tau_cosine  OR  cos_distance(Q, C) = 1 - cos(Q, C) <= delta    │
│ - Complexity: O(D) dot-product projection on unit hypersphere.                            │
│ - Role: Fast coarse rejection of off-topic queries and cross-domain payloads.             │
│ - Classical Blindspot: Adversarial suffixes (AdvBench/GCG) that concentrate perturbations │
│   into a few dimensions while maintaining high global cosine similarity.                  │
└─────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │ PASS (Macro-topic validated)
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ HEAD 2: Excited Dimension Mass Counter (Coarse Resonant Mass)                             │
│ - Metric: N_act = sum_{d=0}^{D-1} I( |Q_d - C_d| <= epsilon_coarse ) >= tau_coarse        │
│ - Precision: Coordinate scale-aware epsilon_coarse derived from E[|v_d|] ≈ 0.03125.       │
│ - Role: Guarantees that vector similarity is distributed across a broad physical mass of  │
│   coordinates, immediately blocking single-dimension spiky adversarial injections.        │
│ - Classical Blindspot: Subtle out-of-distribution queries that accidentally trip enough   │
│   coarse delta registers.                                                                 │
└─────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │ PASS (Coordinate mass validated)
                                              ▼
┌───────────────────────────────────────────────────────────────────────────────────────────┐
│ HEAD 3: Harmonic Subspace Resonance (Microscopic 17-Digit Fine-Tuning Sieve)              │
│ - Metric: Zero-Rounding Coordinate Spectral Quorum across native intervals [lo_d, hi_d]:  │
│     1. Foreign Resonance Quorum: solo_b == 0 (Strict Zero Foreign Band Contamination).    │
│     2. Native Harmonic Mass: solo_a >= tau_floor (Mandatory Native Subspace Energy).      │
│ - Precision: IEEE 754 full-precision float32/float64 (17 significant decimal digits).     │
│ - Role: Sintonía Fina. Microscopic coordinate-level verification across all 1024 dims.    │
│   Eliminates the legacy 64% false-positive collapse and permanently seals semantic leaks. │
└─────────────────────────────────────────────┬─────────────────────────────────────────────┘
                                              │ ALL PASS (Unconditional)
                                              ▼
                                 [ Upstream LLM Dispatch ]
```

---

## 2. The Implementation Tickets Matrix

The roadmap is decomposed into six self-contained, sequentially ordered engineering tickets located in [`roadmap/tickets/`](./roadmap/tickets/README.md). Each ticket is specified with complete mathematical formulas, file targets, and automated test criteria (DoD) for direct assignment to autonomous AI programming agents:

| Ticket ID | Title | Primary Focus | Dependencies | Target Area |
| :--- | :--- | :--- | :--- | :--- |
| **[`TK-01`](./roadmap/tickets/TK01-numerical-purity-enforcement.md)** | **Universal Numerical Purity** | Eradicate `round()`, `:.4f`, float16 in backend math | None | `backend/app/core/`, `storage.py` |
| **[`TK-02`](./roadmap/tickets/TK02-head1-cosine-difference-gate.md)** | **Head 1: Cosine Difference** | Establish Cosine as first macro gate with exact distance | `TK-01` | `backend/app/core/firewall.py` |
| **[`TK-03`](./roadmap/tickets/TK03-head2-excited-dimensions-counter.md)** | **Head 2: Coordinate Mass Counter** | Calibrate $N_{act}$ integer mass with coordinate scale | `TK-01`, `TK-02` | `backend/app/core/firewall.py` |
| **[`TK-04`](./roadmap/tickets/TK04-head3-fine-harmonic-resonance.md)** | **Head 3: Harmonic Resonance** | Implement 17-digit spectral quorum ($solo\_b=0, solo\_a \ge \tau$) | `TK-01`, `TK-03` | `backend/app/core/firewall.py`, `storage.py` |
| **[`TK-05`](./roadmap/tickets/TK05-config-state-and-telemetry-parity.md)** | **Telemetry & Config Parity** | Update `ConfigState`, sniffer SSE, and `/chat` inline logs | `TK-02`, `TK-03`, `TK-04` | `models.py`, `sniffer.py`, `chat.py` |
| **[`TK-06`](./roadmap/tickets/TK06-empirical-benchmark-validation.md)** | **Empirical Benchmark Battery** | Run 215-prompt Prisma/AdvBench suite ($J > 0.95$, $0$ FP) | `TK-05` | `backend/tests/benchmark_suite.py` |

---

## 3. Guiding Rules for Downstream AI Agents

1. **Zero Coward Rounding:** Never introduce `round()`, `np.round()`, `torch.round()`, or string truncation formatters (`:.4f`, `:.6f`) in any analytical or mathematical path.
2. **Lossless Precision Storage:** Coordinate intervals $[lo_d, hi_d]$ and embedding vectors must be stored and evaluated in native IEEE 754 Float32 or Float64.
3. **TDD Strictness:** Every ticket must provide unit tests under `backend/tests/` that pass with 100% green status via `pytest`.
4. **Non-Destructive Evolution:** Do not break existing API routes (`POST /chat`, `POST /v1/chat/completions`); preserve streaming contracts while updating inline telemetry headers.
