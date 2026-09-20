# TK-03: Head 2 — Excited Dimension Mass Counter

> **Ticket ID:** `TK-03`  
> **Status:** `PENDING`  
> **Pre-requisites:** `TK-01`, `TK-02`  
> **Target Subsystem:** Sequential Pipeline — Head 2 (`run_excitation_filter`)  
> **Reference Specs:** [`roadmap.md`](../../roadmap.md) & [`ddi-fw/rfc-numerical-purity-catastrophe.md`](../../ddi-fw/rfc-numerical-purity-catastrophe.md)

---

## 1. Context & Objective

Cosine similarity has a well-documented vulnerability: an adversarial prompt (or clever jailbreak suffix) can concentrate massive mathematical energy on just 3 or 4 dimensions, inflating the dot product average while completely violating the underlying semantic distribution.

**Head 2** acts as the **coarse dimensional mass sieve**. It counts the integer number of dimensions $d \in \{0, \dots, D-1\}$ whose absolute coordinate delta between query $Q$ and nearest corpus chunk $C$ is within a coarse coordinate tolerance $\epsilon_{\text{coarse}}$:

$$N_{\text{act}} = \sum_{d=0}^{D-1} \mathbb{I}(|Q_d - C_d| \le \epsilon_{\text{coarse}})$$
$$\text{Pass Condition: } N_{\text{act}} \ge \tau_{\text{coarse}}$$

This guarantees that the alignment is physically distributed across a broad manifold mass rather than a spiky mathematical anomaly.

**Objective:** Calibrate $\epsilon_{\text{coarse}}$ and $\tau_{\text{coarse}}$ in accordance with true coordinate distribution scale ($\mathbb{E}[|v_d|] \approx 0.03125$), eradicate arbitrary ad-hoc scaling factors, and ensure integer counting on lossless unrounded coordinate deltas.

---

## 2. Scope & Target Files

### Files to Modify
- [`backend/app/core/firewall.py`](../../backend/app/core/firewall.py):
  - In `run_excitation_filter()`:
    - Compute unrounded elementwise delta $\Delta_d = |Q_d - C_d|$.
    - Evaluate boolean activation vector $A_d = (\Delta_d \le \epsilon_{\text{coarse}})$.
    - Sum activations $N_{\text{act}} = \text{int}(\text{np.count\_nonzero}(A_d))$.
    - Support adaptive tolerance for short queries if $L(q) < 6$, but base the adaptation on a continuous exponential decay rather than crude step multipliers.
- [`backend/app/core/models.py`](../../backend/app/core/models.py):
  - Set default `excitation_order = 2` in `ConfigState`.
  - Default `noise_tolerance` (renamed/aliased as `coarse_delta_tolerance`): `0.015` (reflecting $0.5 \times \mathbb{E}[|v_d|]$).
  - Default `excitation_threshold` (coarse mass): `120` to `200` dimensions out of 1024.

---

## 3. Mathematical Requirements

1. **True Coordinate Scale Alignment:**
   Coordinates in BGE-M3 1024D have standard deviation $\sigma \approx 0.031$. A tolerance of $\epsilon = 0.005$ was too tight for 4-decimal precision, while $\epsilon = 0.015$ captures true semantic resonance without false-positive rejection of complex vocabulary.
2. **Deterministic Integer Count:**
   $$N_{\text{act}} \in [0, 1024]$$
3. **Short-Circuit Enforcement:**
   If $N_{\text{act}} < \tau_{\text{coarse}}$, return `passed = False` with `breach_reason = "excitation_mass"`.

---

## 4. Test-Driven Verification (TDD)

1. Create `backend/tests/test_head2_excitation_mass.py`:
   - Test synthetic vector with broad uniform delta $\le \epsilon_{\text{coarse}}$ across 300 dimensions $\implies N_{\text{act}} = 300 \ge \tau \implies \text{PASS}$.
   - Test synthetic adversarial spike vector: high cosine similarity ($\cos = 0.85$) constructed by 2 massive dimensions, but remaining 1022 dimensions have delta $> \epsilon_{\text{coarse}} \implies N_{\text{act}} = 2 < \tau \implies \text{BREACH}$ (Proves Head 2 catches what Head 1 missed!).
2. Run `uv run pytest backend/tests/test_head2_excitation_mass.py`.

---

## 5. Definition of Done (DoD)

- [ ] `run_excitation_filter` runs in position 2 (`order = 2`).
- [ ] Deltas are computed directly on Float32 arrays without intermediate rounding.
- [ ] Synthetic spiky injection test passes, confirming adversarial catch capability.
- [ ] Unit tests pass with 100% success.
