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

config_state = ConfigState()

class ConfigUpdate(BaseModel):
    excitation_threshold: int
    noise_tolerance: float
    cosine_threshold: float

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
            "Eres un asistente técnico. "
            "Basa tu respuesta PRIORITARIAMENTE en el contexto proporcionado. "
            "Si el usuario hace una pregunta que NO tiene relación con el contexto "
            "(ej. recetas de cocina, chistes, temas completamente ajenos), "
            "responde brevemente que no puedes ayudar con esa parte específica, "
            "pero SÍ responde las partes que se relacionan con el contexto."
        )
        full_prompt = f"{system_instruction}\n\nContexto:\n{context}\n\nConsulta del usuario:\n{prompt}"
    else:
        full_prompt = f"Contexto:\n{context}\n\nConsulta del usuario:\n{prompt}"
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
    
    # --- Hybrid Clause Segmentation Firewall ---
    clauses = [c.strip() for c in re.split(r'[.?\n]+|,\s*(?:y|pero|también|además|and|also|plus)\s+', clean_prompt) if len(c.strip()) > 4]
    if not clauses:
        clauses = [clean_prompt]

    context = ""
    failed_clause = None
    block_reason = ""
    activations = 0
    cosine_sim = 0.0
    current_threshold = float(config_state.excitation_threshold)

    for clause in clauses:
        cl_vec = embedder.embed(clause)
        results = storage.search_nearest(cl_vec, k=1)
        if not results:
            seg_activations = 0
            cosine_sim = 0.0
        else:
            db_vec = results[0]["vector"]
            if not context:
                context = results[0]["text"]
            cl_arr = np.array(cl_vec, dtype=np.float32)
            db_arr = np.array(db_vec, dtype=np.float32)
            delta = np.abs(cl_arr - db_arr)
            seg_activations = int(np.sum(delta <= config_state.noise_tolerance))
            cl_norm = np.linalg.norm(cl_arr)
            db_norm = np.linalg.norm(db_arr)
            cosine_sim = float(np.dot(cl_arr, db_arr) / (cl_norm * db_norm)) if cl_norm > 0 and db_norm > 0 else 0.0

        word_count = len(clause.split())
        base_threshold = config_state.excitation_threshold
        current_threshold = base_threshold * 0.85 if word_count < 6 else float(base_threshold)

        if seg_activations < current_threshold:
            failed_clause = clause
            activations = seg_activations
            block_reason = "activations"
            break
        if cosine_sim < config_state.cosine_threshold:
            failed_clause = clause
            activations = seg_activations
            block_reason = "cosine"
            break
        activations = seg_activations
        
    if fw_on:
        if failed_clause is not None:
            if block_reason == "cosine":
                block_msg = (
                    f'🛑 [FIREWALL BLOCKED] Semantic anchoring detected in segment: "{failed_clause}". '
                    f'Cosine Similarity: {cosine_sim:.3f} (Required: ≥{config_state.cosine_threshold:.2f}). '
                    f'Vector direction diverges from sovereign corpus.'
                )
            else:
                block_msg = (
                    f'🛑 [FIREWALL BLOCKED] Violation in segment: "{failed_clause}". '
                    f'Resonance: {activations} (Required: {current_threshold:.0f}).'
                )
            async def breach_stream():
                yield json.dumps({"type": "content", "text": block_msg}).encode("utf-8") + b"\n"
            return StreamingResponse(breach_stream(), media_type="application/x-ndjson")

        # Firewall passed — prepend telemetry badge before the LLM stream
        pass_prefix = (
            f"🟢 [FIREWALL PASSED] Resonance achieved: "
            f"{activations}/{config_state.excitation_threshold} dimensions. "
            f"Routing to sovereign knowledge...\n\n"
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
