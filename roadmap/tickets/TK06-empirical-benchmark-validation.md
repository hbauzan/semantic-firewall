# TK-06: Empirical Benchmark Battery & Youden J Verification

> **Ticket ID:** `TK-06`  
> **Status:** `PENDING`  
> **Pre-requisites:** `TK-01` through `TK-05`  
> **Target Subsystem:** Offline Validation Suite & Evidence Generation  
> **Reference Specs:** [`benchmark-report.md`](../../benchmark-report.md) & [`ddi-fw/rfc-numerical-purity-catastrophe.md`](../../ddi-fw/rfc-numerical-purity-catastrophe.md)

---

## 1. Context & Objective

The historical freeze of `semantic-firewall` at `v2.34.0` was triggered by empirical measurements:
- Excitation alone yielded **0 rescues** over cosine.
- In-domain accuracy collapsed from **96% to 64%** due to false positives.

With Tickets `TK-01` through `TK-05` implemented, the firewall now operates with:
- Head 1: Cosine Difference (Macro orientation)
- Head 2: Excited Coordinate Mass Counter (Broad dimensional support)
- Head 3: 17-digit Fine Harmonic Resonance Sieve ($solo\_b == 0 \land solo\_a \ge \tau_{\text{floor}}$)

**Objective:** Re-run the canonical 215-prompt offline benchmark suite against the Chevrolet Prisma 2016 corpus (`om_ng-chevrolet_Prisma_my15-es_AR.pdf.pdf`), compute Youden's $J$ statistic across the sweep grid, and scientifically prove that Head 3 eliminates false positives and actively intercepts adversarial and off-topic payloads that slip through Head 1.

---

## 2. Dataset Composition (215 Prompts)

| Class | Count | Ground Truth | Description |
| :--- | :---: | :---: | :--- |
| **In-Domain Benign** | 50 | `should_block = False` | Authentic Chevrolet Prisma queries (maintenance, oil, spark plugs, dashboard lights). |
| **Out-of-Distribution (OOD)** | 50 | `should_block = True` | Benign queries from cooking, astronomy, and finance. |
| **AdvBench Jailbreaks** | 100 | `should_block = True` | Standard adversarial prompts (malware, bombs, phishing, exfiltration). |
| **GCG Textual Noise** | 15 | `should_block = True` | Gradient-optimized adversarial character perturbations. |

---

## 3. Scope & Target Files

### Files to Modify / Execute
- [`backend/tests/benchmark_suite.py`](../../backend/tests/benchmark_suite.py):
  - Update `measure_dataset()` to evaluate all three heads independently per clause:
    - `res_head1 = run_cosine_filter(q, c, cfg)`
    - `res_head2 = run_excitation_filter(q, c, cfg)`
    - `res_head3 = run_harmonic_resonance_filter(q, c, bounds_native, bounds_foreign, cfg)`
  - Measure rescues:
    $$\text{Rescued by Head 3} = \sum \mathbb{I}(\text{Blocked by Head 3} \land \text{Passed by Head 1 \& Head 2})$$
  - Compute Youden's index:
    $$J = \text{Sensitivity} + \text{Specificity} - 1 = \frac{TP}{TP + FN} + \frac{TN}{TN + FP} - 1$$
- Generate updated artifacts:
  - `benchmark-report.md` (Update with new results)
  - `backend/tests/benchmark_metrics.csv`
  - `backend/tests/benchmark_roc.png`

---

## 4. Success Criteria (Definition of Done)

- [ ] **In-Domain Accuracy:** In-domain benign queries (50/50) achieve $\ge 96\%$ pass rate (eliminating the legacy 64% false-positive anomaly).
- [ ] **Head 3 Rescues:** Demonstrate strictly $> 0$ attacks rescued exclusively by Head 3 harmonic resonance ($solo\_b > 0$).
- [ ] **Youden J:** Maximum Youden index $J \ge 0.94$.
- [ ] **Reproducibility:** The benchmark suite executes to completion via:
  ```bash
  cd backend && uv run python tests/benchmark_suite.py
  ```
- [ ] Updated `benchmark-report.md` reflects the mathematical vindication of the Three-Headed Semantic Firewall.
