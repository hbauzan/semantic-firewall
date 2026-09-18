"""Config & Profile Endpoints — firewall configuration, profiles, and audit.

Extracted from routes.py as part of Router Decomposition (Finding A1).
Includes:
  - POST /galaxy/config — update firewall config (with auto-calibration)
  - GET  /galaxy/config — return current config for frontend hydration (Finding F5/Q4)
  - GET/POST/DELETE /galaxy/profiles — profile CRUD
  - POST /audit — full pipeline dry-run using evaluate_clause() (Finding F4)
"""
import logging
import numpy as np
from fastapi import APIRouter, HTTPException, Depends, Request

from app.modules.profiles import ProfileManager
from app.modules.embedder import embedder
from app.modules.storage import storage
from app.core.models import ConfigState, ConfigUpdate, AuditRequest
from app.core.state import _config_lock
from app.core.firewall import SemanticFirewall
from app.core.settings import settings
from app.api.endpoints._shared import verify_api_key, limiter
from app.modules.rag_context import accumulate_rag_chunks, join_rag_context

logger = logging.getLogger(__name__)

router = APIRouter()

# --- Configuration Endpoints ---

@router.get("/galaxy/config", dependencies=[Depends(verify_api_key)])
async def get_config():
    """Return current config state for frontend hydration (Finding Q4/F5)."""
    from app.core import state as state_mod
    return {"config": state_mod.config_state.model_dump()}


@router.post("/galaxy/config", dependencies=[Depends(verify_api_key)])
async def update_config(config: ConfigUpdate):
    from app.core import state as state_mod
    try:
        async with _config_lock:
            current = state_mod.config_state
            req_data = config.model_dump()
            if "active_corpus_file" not in config.model_fields_set:
                req_data["active_corpus_file"] = current.active_corpus_file
            if "egress_profile" not in config.model_fields_set:
                req_data["egress_profile"] = current.egress_profile

            # --- Phase 2.1-B: Non-Intrusive Smart Calibration ---
            mode_toggled = req_data["firewall_mode"] != current.firewall_mode

            # Detect per-field user intent: if req value != current value, user moved a slider
            cos_manual = req_data["cosine_threshold"] != current.cosine_threshold
            exc_manual = req_data["excitation_threshold"] != current.excitation_threshold

            # Apply defaults ONLY if mode is toggled AND user didn't touch the slider
            if mode_toggled:
                if req_data["firewall_mode"] == "negative":
                    if not cos_manual:
                        req_data["cosine_threshold"] = 0.6197
                    if not exc_manual:
                        req_data["excitation_threshold"] = 170
                    req_data["global_noise_limit"] = 4.5  # Entropy Floor
                else:
                    if not cos_manual:
                        req_data["cosine_threshold"] = 0.5315
                    if not exc_manual:
                        req_data["excitation_threshold"] = 150
                    req_data["global_noise_limit"] = 4.5

            new_state = ConfigState(**req_data)
            state_mod.config_state = new_state

        ProfileManager.save_profile("_last_used", new_state)
        return {"status": "updated", "config": new_state.model_dump()}
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid configuration values")


# --- Profile Endpoints ---

@router.get("/galaxy/profiles", dependencies=[Depends(verify_api_key)])
async def list_profiles():
    """Return sorted list of user-visible named profiles."""
    return {"profiles": ProfileManager.list_profiles()}


@router.post("/galaxy/profiles/save/{name}", dependencies=[Depends(verify_api_key)])
async def save_profile(name: str):
    """Save current config state under the given profile name."""
    if name.startswith("_"):
        raise HTTPException(status_code=400, detail="Profile names cannot start with underscore (reserved for internal use).")
    from app.core import state as state_mod
    ProfileManager.save_profile(name, state_mod.config_state)
    return {"status": "saved", "profile": name}


@router.post("/galaxy/profiles/load/{name}", dependencies=[Depends(verify_api_key)])
async def load_profile(name: str):
    """Load a named profile and apply it as the active config."""
    data = ProfileManager.load_profile(name)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found.")
    from app.core import state as state_mod
    try:
        async with _config_lock:
            new_state = ConfigState(**data)
            state_mod.config_state = new_state
        ProfileManager.save_profile("_last_used", new_state)
        return {"status": "loaded", "profile": name, "config": new_state.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Invalid profile data: {e}")


@router.delete("/galaxy/profiles/{name}", dependencies=[Depends(verify_api_key)])
async def delete_profile(name: str):
    """Delete a named profile. Protected (underscore-prefixed) profiles cannot be deleted."""
    deleted = ProfileManager.delete_profile(name)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Profile '{name}' not found or protected.")
    return {"status": "deleted", "profile": name}


# --- Audit Endpoint (Finding F4: uses evaluate_clause instead of manual math) ---

@router.post("/audit", dependencies=[Depends(verify_api_key)])
@limiter.limit(settings.rate_limit_chat)
async def audit_query(request: Request, req: AuditRequest):
    """Dry-run the full firewall pipeline against a single query.
    Uses SemanticFirewall.evaluate_clause() to respect pipeline order and filters."""
    from app.core import state as state_mod
    cfg = state_mod.config_state  # immutable snapshot
    q_vec = embedder.embed(req.query)
    results = storage.search_for_firewall(
        q_vec, k=cfg.rag_top_k, active_corpus_file=cfg.active_corpus_file,
    )
    if not results:
        return {"passed": False, "breach_reason": "no_context", "trace": [], "activations": 0, "text": "Empty Database."}

    context_chunks: list[str] = []
    seen: set = set()
    accumulate_rag_chunks(results, context_chunks, seen)
    context = join_rag_context(context_chunks)

    c_vec = results[0]["vector"]
    q_arr = np.array(q_vec, dtype=np.float32)
    c_arr = np.array(c_vec, dtype=np.float32)
    word_count = len(req.query.split())

    result = SemanticFirewall.evaluate_clause(q_arr, c_arr, cfg, word_count)
    trace = list(result["trace"])
    trace.append({
        "stage": "rag_context",
        "passed": True,
        "chunk_count": len(context_chunks),
        "k": cfg.rag_top_k,
        "clauses_with_hits": 1,
    })
    return {
        "passed": result["passed"],
        "breach_reason": result["breach_reason"],
        "trace": trace,
        "activations": result["last_activations"],  # backward compat
        "text": results[0]["text"],
        "context": context,
        "rag_chunk_count": len(context_chunks),
    }
