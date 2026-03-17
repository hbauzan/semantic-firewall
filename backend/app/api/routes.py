import psutil
import torch
import json
import re
import numpy as np
import httpx
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel
from fastapi.responses import StreamingResponse

from app.modules.ingestor import process_pdf_async, get_task_status
from app.modules.embedder import embedder
from app.modules.storage import storage

router = APIRouter()

class ConfigState:
    excitation_threshold: int = 150
    noise_tolerance: float = 0.005
    cosine_threshold: float = 0.78
    global_noise_limit: float = 0.50
    cosine_order: int = 2
    excitation_order: int = 3
    noise_order: int = 1
    adaptive_factor: float = 0.85

config_state = ConfigState()

class ConfigUpdate(BaseModel):
    excitation_threshold: int
    noise_tolerance: float
    cosine_threshold: float
    global_noise_limit: float = 0.50
    cosine_order: int = 2
    excitation_order: int = 3
    noise_order: int = 1
    adaptive_factor: float = 0.85

class AuditRequest(BaseModel):
    query: str

class ChatRequest(BaseModel):
    prompt: str

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

@router.post("/galaxy/config")
async def update_config(config: ConfigUpdate):
    config_state.excitation_threshold = config.excitation_threshold
    config_state.noise_tolerance = config.noise_tolerance
    config_state.cosine_threshold = config.cosine_threshold
    config_state.global_noise_limit = config.global_noise_limit
    config_state.cosine_order = config.cosine_order
    config_state.excitation_order = config.excitation_order
    config_state.noise_order = config.noise_order
    config_state.adaptive_factor = config.adaptive_factor
    return {"status": "updated", "config": config}

@router.post("/audit")
async def audit_query(req: AuditRequest):
    q_vec = embedder.embed(req.query)
    results = storage.search_nearest(q_vec, k=1)
    if not results:
        return {"activations": 0, "text": "Empty Database.", "vector": []}
    
    # Calculate activations
    c_vec = results[0]["vector"]
    activations = 0
    for q_i, c_i in zip(q_vec, c_vec):
        if abs(q_i - c_i) <= config_state.noise_tolerance:
            activations += 1

    return {"activations": activations, "text": results[0]["text"], "vector": c_vec.tolist() if hasattr(c_vec, "tolist") else c_vec}


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
            yield json.dumps({"type": "error", "text": str(e)}).encode("utf-8")

@router.post("/chat")
async def chat_endpoint(req: ChatRequest):
    prompt = req.prompt
    fw_on = "[FW=ON]" in prompt
    clean_prompt = prompt.replace("[FW=ON]", "").replace("[FW=OFF]", "").strip()
    
    # --- Structural Clause Segmentation (Language-Agnostic) ---
    raw_clauses = [c.strip() for c in re.split(r'[.!?;:\n\-\|«»\u201c\u201d]+', clean_prompt) if len(c.strip()) > 4]
    if not raw_clauses:
        raw_clauses = [clean_prompt]

    # Safety fallback: force-split long clauses into ≤15-word sub-chunks
    clauses = []
    for rc in raw_clauses:
        words = rc.split()
        if len(words) > 20:
            for i in range(0, len(words), 15):
                sub = " ".join(words[i:i+15])
                if len(sub.strip()) > 4:
                    clauses.append(sub.strip())
        else:
            clauses.append(rc)
    if not clauses:
        clauses = [clean_prompt]

    # --- Sequential Pipeline Engine ---
    # Define the three filter functions. Each returns (passed: bool, reason: str, details: dict)
    def run_noise_filter(cl_arr, db_arr, clause, **_kw):
        avg_delta = float(np.mean(np.abs(cl_arr - db_arr)))
        if avg_delta > config_state.global_noise_limit:
            return False, "noise", {
                "avg_delta": avg_delta,
                "limit": config_state.global_noise_limit,
                "clause": clause
            }
        return True, "noise", {"avg_delta": avg_delta}

    def run_cosine_filter(cl_arr, db_arr, clause, **_kw):
        cl_norm = np.linalg.norm(cl_arr)
        db_norm = np.linalg.norm(db_arr)
        sim = float(np.dot(cl_arr, db_arr) / (cl_norm * db_norm)) if cl_norm > 0 and db_norm > 0 else 0.0
        if sim < config_state.cosine_threshold:
            return False, "cosine", {"cosine_sim": sim, "clause": clause}
        return True, "cosine", {"cosine_sim": sim}

    def run_excitation_filter(cl_arr, db_arr, clause, word_count=0, **_kw):
        delta = np.abs(cl_arr - db_arr)
        seg_activations = int(np.sum(delta <= config_state.noise_tolerance))
        base_threshold = config_state.excitation_threshold
        is_short = word_count < 6
        factor = config_state.adaptive_factor if is_short else 1.0
        threshold = float(base_threshold) * factor
        if seg_activations < threshold:
            return False, "excitation", {
                "activations": seg_activations,
                "threshold": threshold,
                "clause": clause,
                "adaptive_applied": is_short,
                "adaptive_factor": factor
            }
        return True, "excitation", {
            "activations": seg_activations,
            "threshold": threshold,
            "adaptive_applied": is_short,
            "adaptive_factor": factor
        }

    # Build ordered pipeline from config
    pipeline_stages = sorted([
        (config_state.cosine_order, "cosine", run_cosine_filter),
        (config_state.excitation_order, "excitation", run_excitation_filter),
        (config_state.noise_order, "noise", run_noise_filter),
    ], key=lambda x: x[0])

    context = ""
    failed_clause = None
    block_reason = ""
    block_details = {}
    pipeline_results = []  # telemetry: ordered list of stage results
    last_activations = 0
    last_cosine = 0.0

    for clause in clauses:
        cl_vec = embedder.embed(clause)
        results = storage.search_nearest(cl_vec, k=1)
        if not results:
            # No context — all filters fail
            failed_clause = clause
            block_reason = "no_context"
            block_details = {"clause": clause}
            pipeline_results.append({"stage": "no_context", "passed": False})
            break

        db_vec = results[0]["vector"]
        if not context:
            context = results[0]["text"]
        cl_arr = np.array(cl_vec, dtype=np.float32)
        db_arr = np.array(db_vec, dtype=np.float32)
        word_count = len(clause.split())

        clause_breached = False
        for _order, stage_name, stage_fn in pipeline_stages:
            passed, reason, details = stage_fn(
                cl_arr, db_arr, clause, word_count=word_count
            )
            pipeline_results.append({"stage": stage_name, "passed": passed, **details})
            if passed:
                if "activations" in details:
                    last_activations = details["activations"]
                if "cosine_sim" in details:
                    last_cosine = details["cosine_sim"]
            else:
                failed_clause = clause
                block_reason = reason
                block_details = details
                clause_breached = True
                break  # stop pipeline on first breach

        if clause_breached:
            break

    if fw_on:
        if failed_clause is not None:
            if block_reason == "cosine":
                block_msg = (
                    f'🛑 [FW] Segment violation: "{failed_clause}". '
                    f'Cosine: {block_details.get("cosine_sim", 0):.3f} '
                    f'(Required: >={config_state.cosine_threshold:.2f}). '
                    f'Vector direction diverges from corpus.'
                )
            elif block_reason == "noise":
                block_msg = (
                    f'🛑 [FW] Segment violation: "{failed_clause}". '
                    f'Noise pre-filter: avg_delta={block_details.get("avg_delta", 0):.4f} '
                    f'(Limit: {config_state.global_noise_limit:.3f}).'
                )
            elif block_reason == "no_context":
                block_msg = (
                    f'🛑 [FW] Segment violation: "{failed_clause}". '
                    f'No context match in corpus.'
                )
            else:
                adaptive_note = ""
                if block_details.get("adaptive_applied"):
                    adaptive_note = (
                        f' [ADAPTIVE] Factor: {block_details.get("adaptive_factor", 1.0)}x.'
                    )
                block_msg = (
                    f'🛑 [FW] Segment violation: "{failed_clause}". '
                    f'Resonance: {block_details.get("activations", 0)}/{block_details.get("threshold", 0):.0f}.{adaptive_note}'
                )

            # Include pipeline execution order in telemetry
            stage_summary = " → ".join(
                f'{r["stage"]}:{"OK" if r["passed"] else "BREACH"}'
                for r in pipeline_results
            )
            block_msg += f'\nPipeline: [{stage_summary}]'

            async def breach_stream():
                yield json.dumps({"type": "content", "text": block_msg}).encode("utf-8") + b"\n"
            return StreamingResponse(breach_stream(), media_type="application/x-ndjson")

        # Firewall passed — prepend telemetry badge before the LLM stream
        stage_summary = " → ".join(
            f'{r["stage"]}:OK' for r in pipeline_results
        )
        pass_prefix = (
            f"🟢 [FW PASS] Resonance: "
            f"{last_activations}/{config_state.excitation_threshold} dims | "
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

@router.get("/system/stats")
async def system_stats():
    cpu = psutil.cpu_percent(interval=0.1)
    ram = psutil.virtual_memory().used / (1024 * 1024)
    gpu_percent = 0.0
    try:
        if torch.backends.mps.is_available():
            vram = torch.mps.current_allocated_memory() / (1024 * 1024)
            # Logarithmic-like scaling for Mac MPS (max alloc usually caps lower dynamically)
            gpu_percent = min(100.0, (vram / 40.0))

        elif torch.cuda.is_available():
            vram = torch.cuda.memory_allocated() / (1024 * 1024)
            gpu_percent = min(100.0, (vram / 40.0))
    except Exception:
        pass
    
    return {"cpu": cpu, "ram": ram, "gpu": gpu_percent}
