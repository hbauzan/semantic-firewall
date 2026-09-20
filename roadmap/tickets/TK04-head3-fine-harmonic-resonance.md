# TK-04: Head 3 — Microscopic 17-Digit Fine Harmonic Resonance Gate

> **Ticket ID:** `TK-04`  
> **Status:** `PENDING`  
> **Pre-requisites:** `TK-01`, `TK-03`  
> **Target Subsystem:** Sequential Pipeline — Head 3 (`run_harmonic_resonance_filter`)  
> **Reference Specs:** [`ddi-fw/rfc-numerical-purity-catastrophe.md`](../../ddi-fw/rfc-numerical-purity-catastrophe.md) & [`ddi-fw/dual-gate-spectral-quorum.md`](../../ddi-fw/dual-gate-spectral-quorum.md)

---

## 1. Context & The Mystery Solved

In `v2.34.0`, the third filter ("la abuela", initially framed around vector Shannon entropy or naive fixed deltas) produced a devastating empirical outcome: **0 rescues over cosine** and an in-domain accuracy drop from **96% to 64%**.

The Deletor Hypothesis research in `ddi-fw` proved why:
When coordinates in $\mathbb{R}^{1024}$ are rounded to 4 or 5 decimal places, natural semantic micro-gaps ($10^{-4}$ to $10^{-6}$) are collapsed to zero. Legitimate in-domain queries were rejected because their unrounded coordinates barely stepped outside artificially compressed rounded bounds, while adversarial attacks slipped through blurred boundaries.

**When evaluated with full IEEE 754 precision (17 digits, zero rounding):**
True **Harmonic Subspace Resonance** emerges. Coordinates of distinct semantic domains occupy disjoint or mutually exclusive intervals:
$$I_{\text{native}}(d) = [lo_d, hi_d], \quad I_{\text{foreign}}(d) = [lo_{B, d}, hi_{B, d}]$$

**Head 3** is the **sintonía fina** (fine-tuning sieve) across all 1024 dimensions:
1. It verifies that the query vector resonates inside the native corpus coordinate envelope without foreign domain contamination ($solo\_b == 0$).
2. It verifies that the query possesses sufficient native harmonic energy mass ($solo\_a \ge \tau_{\text{floor}}$).

---

## 2. Scope & Target Files

### Files to Modify
- [`backend/app/core/firewall.py`](../../backend/app/core/firewall.py):
  - Implement `run_harmonic_resonance_filter(q_arr, c_arr, native_bounds, foreign_bounds, tau_floor, cfg) -> tuple[bool, str, dict]`.
  - Evaluate per-dimension coordinate votes across all $D=1024$ dimensions:
    - $v_d \in I_{\text{native}}(d) \land v_d \notin I_{\text{foreign}}(d) \implies solo\_a$
    - $v_d \notin I_{\text{native}}(d) \land v_d \in I_{\text{foreign}}(d) \implies solo\_b$
    - $v_d \in I_{\text{native}}(d) \land v_d \in I_{\text{foreign}}(d) \implies ambas$
    - $v_d \notin I_{\text{native}}(d) \land v_d \notin I_{\text{foreign}}(d) \implies ninguna$
  - **Gate Decision:**
    - If $solo\_b > 0 \implies \text{BREACH ("foreign_band_contamination")}$.
    - If $solo\_a < \tau_{\text{floor}} \implies \text{BREACH ("insufficient_harmonic_resonance")}$.
    - Else $\implies \text{PASS ("harmonic_resonance_validated")}$.
- [`backend/app/modules/storage.py`](../../backend/app/modules/storage.py):
  - Add `get_pack_coordinate_bounds(pack_name) -> tuple[np.ndarray, np.ndarray]`:
    Computes exact elementwise minimum and maximum vectors $[lo, hi]$ for the pack in LanceDB at full IEEE 754 precision without rounding:
    $$lo_d = \min_{c \in \text{pack}} C_{c, d}, \quad hi_d = \max_{c \in \text{pack}} C_{c, d}$$
- [`backend/app/core/models.py`](../../backend/app/core/models.py):
  - Add `harmonic_enabled: bool = True`, `harmonic_order: int = 3`, `harmonic_tau_floor: int = 15`.

---

## 3. Mathematical Requirements

1. **Lossless IEEE 754 Coordinates:**
   Array extraction and interval bounds must use `dtype=np.float32` or `np.float64`. No decimal rounding or `.half()` casting.
2. **Deterministic Vote Recount:**
   $$\text{recuento} = \{ solo\_a: n_a, solo\_b: n_b, ambas: n_{ab}, ninguna: n_0 \}$$
   $$\sum \text{votos} = D = 1024$$
3. **Floor Derivation:**
   $\tau_{\text{floor}} = \lfloor \alpha \cdot \min(solo\_a) \rfloor$ (typically 15–30 dimensions).

---

## 4. Test-Driven Verification (TDD)

1. Create `backend/tests/test_head3_harmonic_resonance.py`:
   - Test legitimate native vector from corpus $\implies solo\_b = 0, solo\_a \ge \tau_{\text{floor}} \implies \text{PASS}$.
   - Test cross-domain contaminated vector (e.g. medical query in automotive corpus) $\implies solo\_b > 0 \implies \text{BREACH}$ with reason `"foreign_band_contamination"`.
   - Test random OOD noise vector $\implies solo\_a < \tau_{\text{floor}} \implies \text{BREACH}$ with reason `"insufficient_harmonic_resonance"`.
   - Test sub-epsilon micro-gap integrity: confirm that micro-gaps of $5 \times 10^{-5}$ separate cleanly without collapse.
2. Run `uv run pytest backend/tests/test_head3_harmonic_resonance.py`.

---

## 5. Definition of Done (DoD)

- [ ] `run_harmonic_resonance_filter` operates as Head 3 (`order = 3`).
- [ ] LanceDB pack bounds are computed and cached losslessly in Float32.
- [ ] Dual-gate voting ($solo\_b == 0 \land solo\_a \ge \tau_{\text{floor}}$) is enforced.
- [ ] All synthetic and corpus tests pass with 100% success.
