# TK-02: Head 1 — Cosine Difference Macro Gate

> **Ticket ID:** `TK-02`  
> **Status:** `DONE`  
> **Pre-requisites:** `TK-01`  
> **Target Subsystem:** Sequential Pipeline — Head 1 (`run_cosine_filter`)  
> **Reference Specs:** [`roadmap.md`](../../roadmap.md) & [`architecture_spec.md`](../../architecture_spec.md)

---

## 1. Context & Objective

Head 1 operates as the **coarse macro-angular filter** of the Three-Headed Semantic Firewall. It calculates the angular projection between the incoming query vector $Q$ and the nearest knowledge corpus vector $C$ on the unit hypersphere $\mathbb{S}^{1023}$.

In positive mode (allowlist containment):
$$\cos(Q, C) = \frac{Q \cdot C}{\|Q\|_2 \|C\|_2}$$
$$\text{Pass Condition: } \cos(Q, C) \ge \tau_{\cos} \quad \iff \quad \text{Angular Distance } (1 - \cos(Q, C)) \le \delta_{\max}$$

If a prompt falls below the cosine threshold, it is immediately discarded in $O(D)$ time without wasting compute on downstream microscopic coordinate inspections.

**Objective:** Consolidate Head 1 as the first gate in the pipeline (`order = 1`), support both cosine similarity ($\cos$) and cosine distance ($1 - \cos$), ensure zero-norm guardrails, and return full IEEE 754 precision in `ClauseResult`.

---

## 2. Scope & Target Files

### Files to Modify
- [`backend/app/core/firewall.py`](../../backend/app/core/firewall.py):
  - Ensure `run_cosine_filter()` computes exact dot products with unrounded Float32/Float64 norms.
  - Return `cosine_sim` and `cosine_distance = 1.0 - cosine_sim` in the details dict.
  - Enforce short-circuit: when Head 1 breaches, pipeline immediately returns `passed = False` with `breach_reason = "cosine"`.
- [`backend/app/core/models.py`](../../backend/app/core/models.py):
  - Set default `cosine_order = 1` in `ConfigState`.
  - Validate that `cosine_threshold` is bounded strictly in $[0.0, 1.0]$.

---

## 3. Mathematical Requirements

1. **Unrounded Norm Calculation:**
   $$q_{\text{norm}} = \sqrt{\sum_{d=0}^{1023} Q_d^2}, \quad c_{\text{norm}} = \sqrt{\sum_{d=0}^{1023} C_d^2}$$
   Zero-norm guard: if $q_{\text{norm}} == 0$ or $c_{\text{norm}} == 0$, immediately breach with reason `"zero_norm"`.
2. **Clipping Invariant:**
   Clip cosine similarity strictly to $[-1.0, 1.0]$ via `np.clip` to prevent floating-point drift beyond mathematical bounds.
3. **Distance Formulation:**
   $$\text{cosine\_dist} = 1.0 - \text{sim}$$

---

## 4. Test-Driven Verification (TDD)

1. Create or expand `backend/tests/test_head1_cosine.py`:
   - Test identical vectors $\implies \cos = 1.0, \text{dist} = 0.0 \implies \text{PASS}$.
   - Test orthogonal vectors $\implies \cos = 0.0 \implies \text{BREACH}$ under positive mode ($\tau_{\cos} = 0.5315$).
   - Test adversarial OOD queries against Chevrolet Prisma corpus $\implies \text{BREACH}$ at Stage 1.
   - Test short-circuit: verify that when Head 1 breaches, Head 2 and Head 3 are not executed.
2. Run `uv run pytest backend/tests/test_head1_cosine.py`.

---

## 5. Definition of Done (DoD)

- [x] `run_cosine_filter` executes as the first stage (`order = 1`).
- [x] Metric calculations preserve exact unrounded floats.
- [x] Telemetry includes both `cosine_sim` and `cosine_distance`.
- [x] 100% unit tests pass for Head 1 (`uv run pytest` from `backend/`: 247 passed, 6 skipped).
