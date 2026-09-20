# TK-05: ConfigState, Real-Time Sniffer & Telemetry Parity

> **Ticket ID:** `TK-05`  
> **Status:** `PENDING`  
> **Pre-requisites:** `TK-02`, `TK-03`, `TK-04`  
> **Target Subsystem:** State Management, Telemetry & API Endpoints  
> **Reference Specs:** [`roadmap.md`](../../roadmap.md) & [`architecture_spec.md`](../../architecture_spec.md)

---

## 1. Context & Objective

With the Three Heads mathematically restored (Head 1 Cosine Difference, Head 2 Excited Coordinate Mass, Head 3 Fine Harmonic Resonance), all operational surfaces must expose unambiguous, structured telemetry.

**Objective:**
1. Update `ConfigState` (`backend/app/core/models.py`) and `manifest.json` to reflect the canonical pipeline order (`cosine` -> `excitation` -> `harmonic`).
2. Update the Real-Time Semantic Sniffer (`backend/app/modules/sniffer.py`) to stream per-head telemetry via SSE without lossy decimal rounding.
3. Update inline ASCII telemetry in `POST /chat` and `POST /v1/chat/completions` (`backend/app/api/endpoints/chat.py`):
   - `[FW_HEAD1_COSINE] sim=... | dist=...`
   - `[FW_HEAD2_MASS] activations=... / 1024 | threshold=...`
   - `[FW_HEAD3_HARMONIC] solo_a=... | solo_b=... | tau_floor=...`

---

## 2. Scope & Target Files

### Files to Modify
- [`manifest.json`](../../manifest.json):
  - Update `state_schema` with:
    - `cosine_order: 1`
    - `excitation_order: 2`
    - `harmonic_order: 3`
    - `harmonic_tau_floor: 15`
    - `harmonic_enabled: true`
- [`backend/app/core/models.py`](../../backend/app/core/models.py):
  - Update `ConfigState` frozen model with the new harmonic fields while preserving backward-compatible aliases for legacy `noise_*` fields.
- [`backend/app/modules/sniffer.py`](../../backend/app/modules/sniffer.py):
  - In `record_audit()`, structure payload to capture `head1`, `head2`, and `head3` telemetry.
- [`backend/app/api/endpoints/chat.py`](../../backend/app/api/endpoints/chat.py):
  - Format `[FIREWALL_AUDIT]` block with ASCII headers:
    ```
    [FIREWALL_AUDIT]
    [FW_HEAD1_COSINE] sim=0.7412 | dist=0.2588 | threshold=0.5315 -> PASS
    [FW_HEAD2_MASS] active=184/1024 | threshold=120 -> PASS
    [FW_HEAD3_HARMONIC] solo_a=42 | solo_b=0 | tau_floor=15 -> PASS
    [FW_STATUS] ALL GATES PASSED -> ROUTING TO UPSTREAM LLM
    ```

---

## 3. Serialization Rules

1. Format all float telemetry values using David Gay's algorithm / standard `str(float(val))` or `f"{val:.6g}"` (only if display-bounded), but keep the raw binary floats in `details` dicts.
2. Ensure SSE JSON events emitted by the Sniffer serialize without truncating mantissas.

---

## 4. Test-Driven Verification (TDD)

1. Create `backend/tests/test_telemetry_parity.py`:
   - Test `GET /galaxy/config` returns correct pipeline orders (1, 2, 3).
   - Test `POST /galaxy/config` allows updating `harmonic_tau_floor` and validates pipeline order uniqueness.
   - Test `POST /chat` returns the exact `[FW_HEAD1_COSINE]`, `[FW_HEAD2_MASS]`, and `[FW_HEAD3_HARMONIC]` headers in NDJSON stream.
2. Run `uv run pytest backend/tests/test_telemetry_parity.py`.

---

## 5. Definition of Done (DoD)

- [ ] `manifest.json` and `ConfigState` match the 3-head canonical schema.
- [ ] `/chat` and `/v1/chat/completions` stream the new telemetry headers.
- [ ] Real-time Sniffer captures all three heads without dropping events.
- [ ] 100% test pass rate across all API tests.
