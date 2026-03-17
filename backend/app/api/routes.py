"""API Routes — thin FastAPI layer.

All firewall math lives in app.core.firewall (SemanticFirewall).
All models live in app.core.models.
All state management lives in app.core.state.
This file handles: HTTP parsing, embedding calls, storage calls, streaming, telemetry formatting.
"""
import os
import psutil
import torch
import json
import numpy as np
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse

from app.modules.ingestor import process_pdf_async, get_task_status
from app.modules.embedder import embedder
from app.modules.storage import storage
from app.core.models import ConfigState, ConfigUpdate, AuditRequest, ChatRequest
from app.core.state import config_state, _config_lock, set_config
from app.core.firewall import SemanticFirewall

# --- Optional API Key Guard ---
_FIREWALL_API_KEY = os.environ.get("FIREWALL_API_KEY")

async def verify_api_key(x_api_key: str | None = Header(default=None)):
    """Opt-in API key check. Only enforced if FIREWALL_API_KEY env var is set."""
    if _FIREWALL_API_KEY and x_api_key != _FIREWALL_API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

router = APIRouter()

# --- Corpus Endpoints ---

@router.post("/corpus/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    file_bytes = await file.read()
    task_id = await process_pdf_async(file_bytes, file.filename)
    return {"task_id": task_id}

@router.get("/corpus/task-status/{task_id}")
async def task_status(task_id: str):
    return get_task_status(task_id)

@router.get("/corpus/packs")
async def list_packs():
    return {"packs": storage.get_summary()}

@router.delete("/corpus/packs/{filename}")
async def delete_pack(filename: str):
    storage.delete_pack(filename)
    return {"status": "deleted", "filename": filename}

# --- Configuration Endpoint ---

@router.post("/galaxy/config", dependencies=[Depends(verify_api_key)])
async def update_config(config: ConfigUpdate):
    from app.core import state as state_mod
    try:
        async with _config_lock:
            state_mod.config_state = ConfigState(**config.model_dump())
        return {"status": "updated", "config": config.model_dump()}
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

# --- Audit Endpoint ---

@router.post("/audit", dependencies=[Depends(verify_api_key)])
async def audit_query(req: AuditRequest):
    from app.core import state as state_mod
    cfg = state_mod.config_state  # immutable snapshot
    q_vec = embedder.embed(req.query)
    results = storage.search_nearest(q_vec, k=1)
    if not results:
        return {"activations": 0, "text": "Empty Database.", "vector": []}

    c_vec = results[0]["vector"]
    activations = 0
    for q_i, c_i in zip(q_vec, c_vec):
        if abs(q_i - c_i) <= cfg.noise_tolerance:
            activations += 1

    return {"activations": activations, "text": results[0]["text"], "vector": c_vec.tolist() if hasattr(c_vec, "tolist") else c_vec}

# --- Ollama Streaming ---

async def stream_ollama(prompt: str, context: str, strict: bool = False):
    if strict:
        system_instruction = (
            "You are a technical assistant. "
            "Base your response PRIMARILY on the provided context. "
            "If the user asks a question that has NO relation to the context "
            "(e.g. recipes, jokes, completely unrelated topics), "
            "briefly state you cannot help with that specific part, "
            "but DO answer the parts that relate to the context."
        )
        full_prompt = f"{system_instruction}\n\nContext:\n{context}\n\nUser query:\n{prompt}"
    else:
        full_prompt = f"Context:\n{context}\n\nUser query:\n{prompt}"
    async with httpx.AsyncClient(timeout=None) as client:
        try:
            async with client.stream(
                "POST",
                "http://localhost:11434/api/generate",
                json={"model": "llama3.1", "prompt": full_prompt, "stream": True}
            ) as response:
                async for chunk in response.aiter_lines():
                    if chunk:
                        yield (chunk + "\n").encode("utf-8")
        except Exception as e:
            yield json.dumps({"response": f"🔴 [LLM OFFLINE] Cannot reach Ollama at localhost:11434. Error: {e}"}).encode("utf-8") + b"\n"

# --- Chat Endpoint (Firewall Gateway) ---

@router.post("/chat", dependencies=[Depends(verify_api_key)])
async def chat_endpoint(req: ChatRequest):
    from app.core import state as state_mod
    cfg = state_mod.config_state  # immutable snapshot — consistent for entire request
    prompt = req.prompt
    # Firewall is active when at least one filter is enabled
    fw_on = cfg.noise_enabled or cfg.cosine_enabled or cfg.excitation_enabled
    # Legacy prefix support: [FW=OFF] forces bypass regardless of toggles
    if "[FW=OFF]" in prompt:
        fw_on = False
    clean_prompt = prompt.replace("[FW=ON]", "").replace("[FW=OFF]", "").strip()

    # Segment prompt via the engine (language-agnostic + overflow chunking)
    clauses = SemanticFirewall.segment(clean_prompt)

    # Evaluate each clause through the ordered pipeline
    context = ""
    failed_clause = None
    block_reason = ""
    block_details = {}
    all_traces = []
    last_activations = 0
    last_cosine = 0.0

    for clause in clauses:
        cl_vec = embedder.embed(clause)
        results = storage.search_nearest(cl_vec, k=1)
        if not results:
            failed_clause = clause
            block_reason = "no_context"
            block_details = {"clause": clause}
            all_traces.append({"stage": "no_context", "passed": False})
            break

        db_vec = results[0]["vector"]
        if not context:
            context = results[0]["text"]
        q_arr = np.array(cl_vec, dtype=np.float32)
        c_arr = np.array(db_vec, dtype=np.float32)
        word_count = len(clause.split())

        result = SemanticFirewall.evaluate_clause(q_arr, c_arr, cfg, word_count)
        all_traces.extend(result["trace"])
        last_activations = result["last_activations"]
        last_cosine = result["last_cosine"]

        if not result["passed"]:
            failed_clause = clause
            block_reason = result["breach_reason"]
            block_details = result["breach_details"]
            break

    # --- Telemetry Formatting & Response ---
    if fw_on:
        if failed_clause is not None:
            block_msg = _format_block_message(
                failed_clause, block_reason, block_details, cfg, all_traces
            )
            async def breach_stream():
                yield json.dumps({"type": "content", "text": block_msg}).encode("utf-8") + b"\n"
            return StreamingResponse(breach_stream(), media_type="application/x-ndjson")

        stage_summary = " → ".join(
            f'{r["stage"]}:OK' for r in all_traces
        )
        pass_prefix = (
            f"🟢 [FW PASS] Resonance: "
            f"{last_activations}/{cfg.excitation_threshold} dims | "
            f"Cosine: {last_cosine:.3f} | "
            f"Pipeline: [{stage_summary}]\n"
            f"Routing to corpus...\n\n"
        )
        async def prefixed_stream():
            yield json.dumps({"response": pass_prefix}).encode("utf-8") + b"\n"
            async for chunk in stream_ollama(clean_prompt, context, strict=True):
                yield chunk
        return StreamingResponse(prefixed_stream(), media_type="application/x-ndjson")

    return StreamingResponse(stream_ollama(clean_prompt, context), media_type="application/x-ndjson")


def _format_block_message(
    failed_clause: str, reason: str, details: dict, cfg: ConfigState, traces: list
) -> str:
    """Format the telemetry block message based on which filter breached."""
    if reason == "cosine":
        msg = (
            f'🛑 [FW] Segment violation: "{failed_clause}". '
            f'Cosine: {details.get("cosine_sim", 0):.3f} '
            f'(Required: >={cfg.cosine_threshold:.2f}). '
            f'Vector direction diverges from corpus.'
        )
    elif reason == "noise":
        msg = (
            f'🛑 [FW] Segment violation: "{failed_clause}". '
            f'Noise pre-filter: avg_delta={details.get("avg_delta", 0):.4f} '
            f'(Limit: {cfg.global_noise_limit:.3f}).'
        )
    elif reason == "no_context":
        msg = (
            f'🛑 [FW] Segment violation: "{failed_clause}". '
            f'No context match in corpus.'
        )
    else:
        adaptive_note = ""
        if details.get("adaptive_applied"):
            adaptive_note = f' [ADAPTIVE] Factor: {details.get("adaptive_factor", 1.0)}x.'
        msg = (
            f'🛑 [FW] Segment violation: "{failed_clause}". '
            f'Resonance: {details.get("activations", 0)}/{details.get("threshold", 0):.0f}.{adaptive_note}'
        )

    stage_summary = " → ".join(
        f'{r["stage"]}:{"OK" if r["passed"] else "BREACH"}' for r in traces
    )
    msg += f'\nPipeline: [{stage_summary}]'
    return msg

# --- System Stats Endpoint ---

@router.get("/system/stats")
async def system_stats():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().used / (1024 * 1024)
    gpu_percent = 0.0
    try:
        if torch.backends.mps.is_available():
            # Apple Silicon: GPU shares unified memory with the system
            allocated = torch.mps.current_allocated_memory()
            total = psutil.virtual_memory().total
            gpu_percent = min(100.0, (allocated / total) * 100.0) if total > 0 else 0.0
        elif torch.cuda.is_available():
            allocated = torch.cuda.memory_allocated()
            total = torch.cuda.get_device_properties(0).total_mem
            gpu_percent = min(100.0, (allocated / total) * 100.0) if total > 0 else 0.0
    except Exception:
        pass

    return {"cpu": cpu, "ram": ram, "gpu": gpu_percent}
