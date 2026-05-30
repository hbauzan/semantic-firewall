# Phase 3: Architectural Hardening — v2.22.0

> **Audit Reference:** `202605291117 - audit_report.md`  
> **Scope:** Findings A1–A4, Q1–Q5, S1–S3, F4  
> **Constraint:** Surgical edits only. No full file rewrites unless creating new modules.

---

## User Review Required

> [!IMPORTANT]
> **Breaking change — Router import path:** `main.py` currently does `from app.api.routes import router`. After Task 1, it will change to `from app.api.router_main import router`. Any external scripts or tools importing from `app.api.routes` will need updating.

> [!WARNING]
> **Test discovery change:** After Task 6, `pytest backend/perform_tests.py` will no longer work. The new command will be `pytest backend/tests/`. The `run_tests.sh` script will be updated accordingly.

> [!IMPORTANT]
> **Frontend CSS extraction (Task 5b):** Inline styles from `ControlPanel.tsx` and `TelemetryHUD.tsx` will be moved to `src/styles/ControlPanel.css`. This is a visual-neutral refactor — no design changes — but please verify the UI after the change.

---

## Open Questions

> [!IMPORTANT]
> **Q1 — Zustand slice granularity:** The audit suggests 3 slices: Firewall Config, Chat Messages, Sniffer Logs. Should `ingestionStatus`, `telemetry`, and `systemAction` go into the Chat slice or a separate System slice?  
> **Default plan:** Group them into the Chat slice since they're displayed alongside chat. We can refine later.

> [!IMPORTANT]
> **Q2 — `stream_ollama` removal scope:** The `/chat` endpoint currently uses `stream_ollama()` which has its own strict-mode system prompt injection. When we unify it through the provider pattern, we need to decide: should the strict system prompt be injected *before* calling `provider.stream_chat()` (by prepending to the messages array), or should we add a `stream_chat_with_context()` method to `BaseProvider`?  
> **Default plan:** Prepend the system prompt as a `system` role message in the messages array before calling `provider.stream_chat()`. This keeps providers simple.

> [!IMPORTANT]
> **Q3 — `perform_tests.py` preservation:** Should the original `perform_tests.py` be deleted after partitioning, or kept as a thin re-export shim for backward compatibility?  
> **Default plan:** Delete it. Update `run_tests.sh` to point to `backend/tests/`.

---

## Proposed Changes

### Task 1 — Backend Router Decomposition (Finding A1)

Split the 583-line monolith [routes.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/routes.py) into focused endpoint modules under a new `app/api/endpoints/` directory.

---

#### [NEW] [\_\_init\_\_.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/endpoints/__init__.py)

Empty package init.

#### [NEW] [corpus.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/endpoints/corpus.py)

- `POST /corpus/upload-pdf` — PDF upload with size/magic/filename validation
- `GET /corpus/task-status/{task_id}` — Async task status polling
- `GET /corpus/packs` — List loaded corpus packs
- `DELETE /corpus/packs/{filename}` — Delete a corpus pack
- Imports: `verify_api_key`, `limiter` from shared dependencies, `_PDF_MAGIC`, `_SAFE_FILENAME_RE`

#### [NEW] [config.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/endpoints/config.py)

- `POST /galaxy/config` — Update firewall config (with auto-calibration)
- **`GET /galaxy/config`** — **NEW endpoint** (Finding F5): Returns current `config_state.model_dump()` for frontend hydration
- `GET /galaxy/profiles` — List profiles
- `POST /galaxy/profiles/save/{name}` — Save profile
- `POST /galaxy/profiles/load/{name}` — Load profile
- `DELETE /galaxy/profiles/{name}` — Delete profile

#### [NEW] [chat.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/endpoints/chat.py)

- `POST /chat` — Firewall gateway + streaming (unified with provider pattern — see Task 2)
- `POST /v1/chat/completions` — OpenAI-compatible proxy with FPI
- Helper: `_format_block_message()` (moved from routes.py)
- Provider is resolved lazily via `get_provider()` inside request handlers (not at module level)

#### [NEW] [system.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/endpoints/system.py)

- `GET /health` — Liveness probe
- `GET /system/stats` — CPU/RAM/GPU telemetry
- `GET /v1/sniffer/stream` — SSE sniffer stream

#### [NEW] [router_main.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/router_main.py)

Entry point that creates a single `APIRouter` and includes sub-routers:
```python
from fastapi import APIRouter
from app.api.endpoints import corpus, config, chat, system

router = APIRouter()
router.include_router(corpus.router)
router.include_router(config.router)
router.include_router(chat.router)
router.include_router(system.router)
```

#### [MODIFY] [main.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/main.py)

- Change `from app.api.routes import router` → `from app.api.router_main import router`

#### [DELETE] [routes.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/routes.py)

Replaced by the decomposed endpoint modules. The original file will be removed after all endpoints are migrated and tests pass.

---

### Task 2 — Provider & Chat Unification (Findings Q3, A2, S1)

---

#### [MODIFY] [chat.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/endpoints/chat.py)

**Remove `stream_ollama()`:** The `/chat` endpoint will use the `BaseProvider` strategy pattern via `get_provider().stream_chat()`. The strict system prompt will be prepended as a system-role message in the messages array.

**Lazy init:** `get_provider()` is called inside each request handler (not at module scope). This prevents boot-time crashes if `GOOGLE_API_KEY` is missing but `UPSTREAM_PROVIDER=google`.

```python
# Before (module-level — crashes on import):
provider = get_provider()

# After (per-request — lazy):
async def chat_endpoint(...):
    provider = get_provider()
    ...
```

The `/chat` endpoint's NDJSON response format will be preserved by wrapping the SSE output from `provider.stream_chat()` into NDJSON lines (extracting `choices[0].delta.content` from each SSE chunk).

#### [MODIFY] [google.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/modules/providers/google.py)

**Security (S1):** Move API key from URL query parameter to `x-goog-api-key` header:
```diff
-url = f"...?alt=sse&key={api_key}"
+url = f"...?alt=sse"
+headers = {"x-goog-api-key": api_key}
 async with client.stream("POST", url, json=..., headers=headers) as response:
```

---

### Task 3 — Security Hardening (Findings S3, F4)

---

#### [MODIFY] [profiles.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/modules/profiles.py)

**Path Traversal (S3):** Add `_SAFE_PROFILE_RE` regex validation at the top of `save_profile()`, `load_profile()`, and `delete_profile()`:
```python
_SAFE_PROFILE_RE = re.compile(r'^[a-zA-Z0-9_\-]{1,64}$')

@staticmethod
def _validate_name(name: str) -> None:
    if not _SAFE_PROFILE_RE.match(name):
        raise ValueError(f"Invalid profile name: '{name}'")
```
Each public method calls `_validate_name(name)` before any disk I/O. The `_last_used` internal profile name passes the regex (underscores are allowed).

#### [MODIFY] [chat.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/endpoints/config.py)

**Audit Alignment (F4):** Refactor the `/audit` endpoint to use `SemanticFirewall.evaluate_clause()` instead of the manual activation count loop. The response will return the full pipeline result:
```python
@router.post("/audit", ...)
async def audit_query(request: Request, req: AuditRequest):
    ...
    result = SemanticFirewall.evaluate_clause(q_arr, c_arr, cfg, word_count)
    return {
        "passed": result["passed"],
        "breach_reason": result["breach_reason"],
        "trace": result["trace"],
        "text": results[0]["text"],
        "activations": result["last_activations"],  # backward compat
    }
```

> [!NOTE]
> The `/audit` endpoint will be placed in `config.py` alongside other config-related endpoints, since auditing is a diagnostic/config function, not a chat function. Alternatively it could go in `system.py` — let me know if you prefer that.

---

### Task 4 — Engine & State Refinement (Findings Q1, Q4)

---

#### [MODIFY] [firewall.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/core/firewall.py)

**Typed Returns (Q1):** Define `ClauseResult` TypedDict and update `evaluate_clause()` return type:
```python
from typing import TypedDict

class ClauseResult(TypedDict):
    passed: bool
    breach_reason: str | None
    breach_details: dict | None
    trace: list[dict]
    last_activations: int
    last_cosine: float
```

The method signature changes from `-> dict` to `-> ClauseResult`. No runtime behavior change — this is purely a type annotation improvement.

#### [NEW] [config.py endpoint](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/endpoints/config.py)

**GET /galaxy/config (Q4):** New endpoint that returns current config state:
```python
@router.get("/galaxy/config", dependencies=[Depends(verify_api_key)])
async def get_config():
    from app.core import state as state_mod
    return {"config": state_mod.config_state.model_dump()}
```

#### [MODIFY] [ControlPanel.tsx](file:///Users/hbauzan/treepwood/semantic-firewall/frontend/src/components/ControlPanel.tsx)

**State Hydration:** Add a `useEffect` on mount that fetches `GET /galaxy/config` and hydrates the Zustand store with backend state. This eliminates the desync where frontend defaults (`globalNoiseLimit: 0.50`) diverge from backend state (`4.5`):

```typescript
useEffect(() => {
  fetch(`${API_BASE_URL}/galaxy/config`)
    .then(res => res.json())
    .then(data => {
      const c = data.config;
      setExcitationThreshold(c.excitation_threshold);
      setCosineThreshold(c.cosine_threshold);
      // ... all fields
    })
    .catch(err => console.error("Failed to hydrate config:", err));
}, []);
```

---

### Task 5 — Frontend State & UI Cleanup (Findings A4, Q2)

---

#### [MODIFY] [store.ts](file:///Users/hbauzan/treepwood/semantic-firewall/frontend/src/store.ts)

**Zustand Slices (A4):** Refactor the monolithic store into 3 slices using the slice pattern:

1. **`createFirewallSlice`** — All config fields + setters (excitationThreshold, cosineThreshold, noiseEnabled, firewallMode, etc.)
2. **`createChatSlice`** — messages, telemetry, systemAction, ingestionStatus + their setters
3. **`createSnifferSlice`** — snifferLogs, snifferFilter + their setters

The exported `useStore` hook remains identical — consumers don't need to change:
```typescript
export const useStore = create<StoreState>()((...a) => ({
  ...createFirewallSlice(...a),
  ...createChatSlice(...a),
  ...createSnifferSlice(...a),
}));
```

The `StoreState` interface is split into `FirewallSlice`, `ChatSlice`, `SnifferSlice` and then combined via intersection.

#### [NEW] [ControlPanel.css](file:///Users/hbauzan/treepwood/semantic-firewall/frontend/src/styles/ControlPanel.css)

**CSS Extraction (Q2):** Extract all inline style objects from `ControlPanel.tsx` and `TelemetryHUD.tsx` into CSS classes. Key extractions:

| Inline Style Object | CSS Class |
|---|---|
| `toggleStyle(on)` | `.toggle-btn`, `.toggle-btn--on`, `.toggle-btn--off` |
| `seqInputStyle` | `.seq-input` |
| `stepBtnStyle` | `.step-btn` |
| Firewall mode banner | `.firewall-mode-banner`, `.firewall-mode-banner--negative` |
| Filter slider groups | `.filter-group`, `.filter-group--disabled` |
| MonkeyHead styles | `.monkey-head`, `.monkey-head--alive`, `.monkey-head--dead` |
| Telemetry bar | `.telemetry-line` |

#### [MODIFY] [ControlPanel.tsx](file:///Users/hbauzan/treepwood/semantic-firewall/frontend/src/components/ControlPanel.tsx)

Replace inline `style={{...}}` props with `className` references. Remove the `toggleStyle()`, `seqInputStyle`, `stepBtnStyle` function/objects.

#### [MODIFY] [TelemetryHUD.tsx](file:///Users/hbauzan/treepwood/semantic-firewall/frontend/src/components/TelemetryHUD.tsx)

Replace inline `style={{...}}` props with `className` references to classes defined in `ControlPanel.css`.

---

### Task 6 — Test Partitioning (Finding Q5)

Split the 931-line [perform_tests.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/perform_tests.py) into focused test modules.

---

#### [NEW] [test_engine.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/tests/test_engine.py)

Pure firewall engine tests (no HTTP):
- `test_engine_segment_basic`
- `test_engine_segment_overflow_chunking`
- `test_engine_evaluate_clause_all_pass`
- `test_engine_evaluate_clause_noise_breach`
- `test_engine_negative_mode_identical_vectors_breach`
- `test_engine_negative_mode_divergent_vectors_pass`
- `test_engine_positive_mode_identical_vectors_pass`
- `test_adaptive_factor_default`
- `test_config_state_is_immutable`
- `test_duplicate_pipeline_orders_rejected`
- `test_config_validation_out_of_range`
- `test_disabled_filter_skipped_in_pipeline`
- `test_all_filters_disabled_bypasses_firewall`
- `test_firewall_mode_default_is_positive`
- `test_firewall_mode_rejects_invalid_value`
- `test_rag_top_k_default`
- `test_rag_top_k_validation`
- `test_adaptive_inversion_negative_mode`
- `test_entropy_low_for_collapsed_vector`
- `test_entropy_high_for_natural_vector`

#### [NEW] [test_api.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/tests/test_api.py)

HTTP endpoint and integration tests:
- `test_async_pdf_upload_and_status`
- `test_dimensional_excitation_math`
- `test_firewall_interceptor_blocking`
- `test_rag_context_injection`
- `test_system_stats_gpu_telemetry`
- `test_semantic_piggybacking_rejection`
- `test_noise_prefilter_entropy_telemetry`
- `test_pipeline_order_respected`
- `test_pipeline_config_sync`
- `test_config_sync_with_enabled_flags`
- `test_health_endpoint`
- `test_openai_proxy_v1_compliance`
- `test_config_sync_includes_rag_top_k`
- `test_config_sync_includes_firewall_mode`
- `test_negative_mode_chat_endpoint`
- `test_adaptive_factor_telemetry_on_short_clause`
- `test_auto_calibration_negative_mode`
- `test_auto_calibration_positive_mode`
- `test_non_intrusive_calibration`
- `test_config_profiles_persistence`
- `test_sniffer_persistence`
- `test_rtss_telemetry_flow`
- `test_sniffer_fpi_request_history`
- `test_sniffer_update_trace_reconstruction`
- **NEW:** `test_get_config_endpoint` — validates the new GET /galaxy/config endpoint
- **NEW:** `test_audit_uses_full_pipeline` — validates audit uses `evaluate_clause()`

#### [NEW] [test_security.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/tests/test_security.py)

Security-focused tests:
- `test_prompt_length_limit_rejected`
- `test_prompt_length_limit_accepted`
- `test_api_key_not_enforced_by_default`
- `test_provider_factory_logic`
- **NEW:** `test_profile_path_traversal_rejected` — validates `_SAFE_PROFILE_RE` rejects `../../etc/passwd`
- **NEW:** `test_google_api_key_in_header` — validates key is sent via header, not URL

#### [NEW] [conftest.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/tests/conftest.py)

Shared fixtures: `client` (TestClient), `set_config` import, common config reset fixture.

#### [DELETE] [perform_tests.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/perform_tests.py)

Replaced by the partitioned test modules.

#### [MODIFY] [run_tests.sh](file:///Users/hbauzan/treepwood/semantic-firewall/run_tests.sh)

Update test command from `pytest backend/perform_tests.py` to `pytest backend/tests/`.

---

### Task 7 — Documentation Updates

---

#### [MODIFY] [manifest.json](file:///Users/hbauzan/treepwood/semantic-firewall/manifest.json)

- Bump `version` from `v2.21.0` to `v2.22.0`
- Add feature flags:
  - `router_decomposition_v1: true`
  - `provider_unification_chat: true`
  - `google_api_header_auth: true`
  - `profile_path_traversal_protection: true`
  - `audit_pipeline_alignment: true`
  - `zustand_slice_refactor: true`
  - `css_module_extraction: true`
  - `test_suite_partitioning: true`
  - `config_hydration_get_endpoint: true`

#### [MODIFY] [architecture_spec.md](file:///Users/hbauzan/treepwood/semantic-firewall/architecture_spec.md)

- **Section 2:** Update directory tree to reflect `app/api/endpoints/` structure with `router_main.py`
- **Section 2 — Routes:** Document the sub-router decomposition
- **Section 9.1:** Update Google Gemini security note (header instead of query param)
- **Section 9.2:** Document lazy provider instantiation
- **Section 11.5:** Add `GET /galaxy/config` to the profile API table
- **Section 11.2:** Document `_SAFE_PROFILE_RE` path traversal protection
- **NEW Section:** Document `ClauseResult` TypedDict
- **Section 5:** Update frontend store architecture (slice pattern)

---

## Verification Plan

### Automated Tests

```bash
# 1. Run the new partitioned test suite
cd backend && python -m pytest tests/ -v --tb=short

# 2. Verify no import errors in the new router structure
python -c "from app.api.router_main import router; print('Router OK')"

# 3. Verify the GET /galaxy/config endpoint works
python -c "
from fastapi.testclient import TestClient
from app.main import app
c = TestClient(app)
r = c.get('/galaxy/config')
assert r.status_code == 200
assert 'config' in r.json()
print('GET /galaxy/config OK')
"

# 4. Verify path traversal protection
python -c "
from app.modules.profiles import ProfileManager
try:
    ProfileManager.save_profile('../../etc/passwd', None)
    print('FAIL: should have rejected')
except ValueError:
    print('Path traversal protection OK')
"

# 5. Frontend build check
cd frontend && npm run build
```

### Manual Verification

- Start the backend (`python -m uvicorn app.main:app`) and confirm all endpoints respond
- Open the frontend and verify:
  - ControlPanel loads with correct values from backend (hydration test)
  - All sliders, toggles, and profile operations work
  - CSS extraction hasn't changed visual appearance
  - Sniffer tab functions correctly

---

## Execution Order

| Step | Task | Dependencies |
|------|------|-------------|
| 1 | Task 3a — ProfileManager path traversal | None |
| 2 | Task 4a — ClauseResult TypedDict | None |
| 3 | Task 2b — Google API key header fix | None |
| 4 | Task 1 — Router decomposition + Task 2a (provider unification) + Task 3b (audit alignment) + Task 4b (GET /galaxy/config) | Steps 1–3 |
| 5 | Task 6 — Test partitioning | Step 4 |
| 6 | Task 5a — Zustand slices | None (parallel with backend) |
| 7 | Task 5b — CSS extraction + Task 4c (config hydration) | Step 6 |
| 8 | Task 7 — Documentation | All above |
| 9 | Run full test suite & verify | All above |
