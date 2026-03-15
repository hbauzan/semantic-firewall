import psutil
import torch
import json
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

config_state = ConfigState()

class ConfigUpdate(BaseModel):
    excitation_threshold: int
    noise_tolerance: float

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


async def stream_ollama(prompt: str, context: str):
    full_prompt = f"Context: {context}\n\nQuery: {prompt}"
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
    
    q_vec = embedder.embed(clean_prompt)
    results = storage.search_nearest(q_vec, k=1)
    
    context = ""
    activations = 0
    if results:
        c_vec = results[0]["vector"]
        context = results[0]["text"]
        activations = sum(1 for q_i, c_i in zip(q_vec, c_vec) if abs(q_i - c_i) <= config_state.noise_tolerance)
        
    if fw_on:
        if activations < config_state.excitation_threshold:
            block_msg = (
                f"🛑 [FIREWALL BLOCKED] Query rejected. "
                f"Dimensional Resonance ({activations}/1024) failed to meet the "
                f"critical threshold ({config_state.excitation_threshold}). "
                f"Semantic contamination detected."
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
            async for chunk in stream_ollama(clean_prompt, context):
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
