# TK-01: Universal Numerical Purity & Decimal Truncation Remediation

> **Ticket ID:** `TK-01`  
> **Status:** `DONE`  
> **Pre-requisites:** None  
> **Target Subsystem:** Mathematical Foundations & Serialization  
> **Reference Specs:** [`ddi-fw/rfc-numerical-purity-catastrophe.md`](../../ddi-fw/rfc-numerical-purity-catastrophe.md) & [`ddi-fw/universal-remediation-directive.md`](../../ddi-fw/universal-remediation-directive.md)

---

## 1. Context & Objective

In high-dimensional embedding spaces ($\mathbb{R}^{1024}$), coordinate magnitudes reside almost exclusively within $[-0.15, +0.15]$, with mean absolute magnitude $\mathbb{E}[|v_d|] \approx 0.03125$. Natural language semantic domains segregate along coordinate boundaries with micro-gaps between $10^{-4}$ and $10^{-6}$.

Applying `round(x, 4)`, `f"{val:.4f}"`, or downcasting to `float16` acts as a catastrophic truncation operator that destroys boundary intervals, collapses semantic distance, and induces false overlaps.

**Objective:** Systematically audit the backend, eradicate all truncation and rounding functions from computational and analytical paths, and enforce native IEEE 754 Float32/Float64 representation with full-mantissa serialization (`f"{float(val):.17g}"` or native float conversion).

---

## 2. Scope & Target Files

### Files to Inspect and Remediate
- [`backend/app/core/firewall.py`](../../backend/app/core/firewall.py): Remove any internal rounding on deltas, activations, entropies, and similarities.
- [`backend/app/modules/storage.py`](../../backend/app/modules/storage.py): Ensure LanceDB vector schemas store unquantized Float32/Float64 vectors; ensure vector queries do not cast to Float16.
- [`backend/app/modules/corpus_calibration.py`](../../backend/app/modules/corpus_calibration.py): Remove rounding in threshold sweeping and metric calculation.
- [`backend/app/core/models.py`](../../backend/app/core/models.py): Ensure Pydantic fields for thresholds do not enforce rounded serialization.
- [`backend/tools/audit_precision.py`](../../ddi-fw/audit_precision.py): Use as validation tool.

---

## 3. Strict Invariants

1. **Zero `round()` in Math:** Prohibit `round()`, `np.round()`, `torch.round()` anywhere in vector math, interval computation, or threshold comparisons.
2. **Mandatory IEEE 754 Formatting:** If a floating-point number must be converted to a string (for logs, CSVs, JSON, or telemetry), it MUST use `f"{float(val):.17g}"` or `str(float(val))`. Never `:.4f` or `:.6f`.
3. **Lossless Vector Arrays:** NumPy arrays holding embeddings must be explicitly typed as `np.float32` or `np.float64`. Never `np.float16`.

---

## 4. Test-Driven Verification (TDD)

1. Write `backend/tests/test_numerical_purity.py`:
   - Test that vector operations preserve bit-level exactness across round-trips.
   - Test that two synthetic coordinates separated by $\Delta = 1.0 \times 10^{-5}$ maintain strict separation and are not merged by any formatting or normalization routine.
   - Assert that no function in `firewall.py` calls Python's built-in `round()`.
2. Run `uv run pytest backend/tests/test_numerical_purity.py`.
3. Run the existing test suite (`uv run pytest`) to ensure all 118 tests pass with unrounded precision.

---

## 5. Definition of Done (DoD)

- [x] Zero occurrences of `round(` or `np.round(` in `backend/app/core/` and `backend/app/modules/`.
- [x] String serializations in telemetry and exports use `%.17g`.
- [x] `backend/tests/test_numerical_purity.py` passes with 100% success.
- [x] Existing unit tests pass without errors (`uv run pytest` from `backend/`: 239 passed, 6 skipped).
