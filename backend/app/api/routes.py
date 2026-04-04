"""API Routes — thin FastAPI layer.

All firewall math lives in app.core.firewall (SemanticFirewall).
All models live in app.core.models.
All state management lives in app.core.state.
This file handles: HTTP parsing, embedding calls, storage calls, streaming, telemetry formatting.
"""
import hmac
import logging
import os
import re
import psutil
import torch
import json
import numpy as np
import httpx
from fastapi import APIRouter, UploadFile, File, HTTPException, Header, Depends, Request
from fastapi.responses import StreamingResponse
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# --- Upload constraints ---
_PDF_MAGIC = b"%PDF"
_SAFE_FILENAME_RE = re.compile(r'^[\w\s.\-()]+\.pdf$', re.UNICODE | re.IGNORECASE)

from app.modules.ingestor import process_pdf_async, get_task_status
from app.modules.embedder import embedder
from app.modules.storage import storage
from app.modules.sniffer import emit_trace, update_trace, subscribe, unsubscribe, stream_sniffer_sse
from app.core.models import ConfigState, ConfigUpdate, AuditRequest, ChatRequest, OpenAIConfig
from app.core.state import _config_lock
from app.core.firewall import SemanticFirewall
from app.core.settings import settings
from app.modules.providers.ollama import OllamaProvider

# --- Rate Limiter (shared instance from app.state, resolved at request time) ---
limiter = Limiter(key_func=get_remote_address)

# --- Optional API Key Guard ---

async def verify_api_key(x_api_key: str | None = Header(default=None)):
    """Opt-in API key check. Only enforced if FIREWALL_API_KEY env var is set.
    Uses hmac.compare_digest for constant-time comparison (timing-attack safe)."""
    api_key = settings.api_key_value
    if api_key:
        if not x_api_key or not hmac.compare_digest(x_api_key, api_key):
            raise HTTPException(status_code=403, detail="Invalid or missing API key")

router = APIRouter()

# --- Provider Abstraction ---
provider = OllamaProvider()

# --- Corpus Endpoints ---

@router.post("/corpus/upload-pdf", dependencies=[Depends(verify_api_key)])
@limiter.limit(settings.rate_limit_upload)
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    # --- File size guard: read in chunks to reject oversized payloads early ---
    chunks: list[bytes] = []
    total = 0
    limit = settings.max_upload_bytes
    while True:
        chunk = await file.read(1024 * 256)  # 256 KB per read
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit")
        chunks.append(chunk)
    file_bytes = b"".join(chunks)

    # --- PDF magic-byte validation ---
    if not file_bytes[:4].startswith(_PDF_MAGIC):
        raise HTTPException(status_code=400, detail="File is not a valid PDF")

    # --- Filename sanitization ---
    raw_name = file.filename or "upload.pdf"
    safe_name = os.path.basename(raw_name)
    if not _SAFE_FILENAME_RE.match(safe_name):
        safe_name = re.sub(r'[^\w.\-]', '_', safe_name)
        if not safe_name.lower().endswith('.pdf'):
            safe_name += '.pdf'

    task_id = await process_pdf_async(file_bytes, safe_name)
    return {"task_id": task_id}

@router.get("/corpus/task-status/{task_id}", dependencies=[Depends(verify_api_key)])
async def task_status(task_id: str):
    return get_task_status(task_id)

@router.get("/corpus/packs", dependencies=[Depends(verify_api_key)])
async def list_packs():
    return {"packs": storage.get_summary()}

@router.delete("/corpus/packs/{filename}", dependencies=[Depends(verify_api_key)])
async def delete_pack(filename: str):
    try:
        storage.delete_pack(filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename: contains disallowed characters")
    return {"status": "deleted", "filename": filename}

# --- Configuration Endpoint ---

@router.post("/galaxy/config", dependencies=[Depends(verify_api_key)])
async def update_config(config: ConfigUpdate):
    from app.core import state as state_mod
    try:
        async with _config_lock:
            state_mod.config_state = ConfigState(**config.model_dump())
        return {"status": "updated", "config": config.model_dump()}
    except ValueError:
        raise HTTPException(status_code=422, detail="Invalid configuration values")

# --- Audit Endpoint ---

@router.post("/audit", dependencies=[Depends(verify_api_key)])
@limiter.limit(settings.rate_limit_chat)
async def audit_query(request: Request, req: AuditRequest):
    from app.core import state as state_mod
    cfg = state_mod.config_state  # immutable snapshot
    q_vec = embedder.embed(req.query)
    results = storage.search_nearest(q_vec, k=cfg.rag_top_k)
    if not results:
        return {"activations": 0, "text": "Empty Database."}

    c_vec = results[0]["vector"]
    activations = 0
    for q_i, c_i in zip(q_vec, c_vec):
        if abs(q_i - c_i) <= cfg.noise_tolerance:
            activations += 1

    return {"activations": activations, "text": results[0]["text"]}

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
    async with httpx.AsyncClient(timeout=httpx.Timeout(connect=10.0, read=300.0, write=10.0, pool=10.0)) as client:
        try:
            async with client.stream(
                "POST",
                f"{settings.ollama_base_url}/api/generate",
                json={"model": settings.ollama_model, "prompt": full_prompt, "stream": True}
            ) as response:
                if response.status_code != 200:
                    logger.error("Ollama returned status %d", response.status_code)
                    yield json.dumps({"response": "🔴 [LLM ERROR] The language model returned an error."}).encode("utf-8") + b"\n"
                    return
                async for chunk in response.aiter_lines():
                    if chunk:
                        # Validate each line is valid JSON before forwarding
                        try:
                            json.loads(chunk)
                            yield (chunk + "\n").encode("utf-8")
                        except json.JSONDecodeError:
                            logger.warning("Dropping malformed Ollama line: %s", chunk[:200])
        except Exception as e:
            logger.error("Ollama connection failed: %s", e)
            yield json.dumps({"response": "🔴 [LLM OFFLINE] Cannot reach the language model. Ensure the inference server is running."}).encode("utf-8") + b"\n"

# --- Chat Endpoint (Firewall Gateway) ---

@router.post("/chat", dependencies=[Depends(verify_api_key)])
@limiter.limit(settings.rate_limit_chat)
async def chat_endpoint(request: Request, req: ChatRequest):
    from app.core import state as state_mod
    cfg = state_mod.config_state  # immutable snapshot — consistent for entire request
    prompt = req.prompt
    # Firewall is active when at least one filter is enabled in the HUD.
    # There is NO user-prompt override — bypass is only possible via the HUD toggles.
    fw_on = cfg.noise_enabled or cfg.cosine_enabled or cfg.excitation_enabled
    clean_prompt = prompt.strip()

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

    negative = cfg.firewall_mode == "negative"

    for clause in clauses:
        cl_vec = embedder.embed(clause)
        results = storage.search_nearest(cl_vec, k=cfg.rag_top_k)
        if not results:
            if negative:
                # Negative mode: no corpus match → nothing to restrict → PASS
                all_traces.append({"stage": "no_context", "passed": True})
                continue
            else:
                # Positive mode: no corpus match → can't verify alignment → BREACH
                failed_clause = clause
                block_reason = "no_context"
                block_details = {"clause": clause}
                all_traces.append({"stage": "no_context", "passed": False})
                break

        db_vec = results[0]["vector"]
        if not context:
            # Concatenate text from all top-K chunks for richer RAG context
            context = "\n---\n".join(r["text"] for r in results)
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
            f'{r["stage"]}:{"OK" if r["passed"] else "MISS"}' for r in all_traces
        )
        mode_label = "NEGATIVE" if negative else "POSITIVE"
        pass_prefix = (
            f"🟢 [FW PASS] [{mode_label}] Resonance: "
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
    negative = cfg.firewall_mode == "negative"
    mode_tag = " [NEGATIVE]" if negative else ""

    # Strip mode prefix for matching (e.g. "negative:cosine" → "cosine")
    bare_reason = reason.split(":", 1)[-1] if reason.startswith("negative:") else reason

    if bare_reason == "cosine":
        if negative:
            msg = (
                f'🛑 [FW]{mode_tag} Restricted content detected: "{failed_clause}". '
                f'Cosine: {details.get("cosine_sim", 0):.3f} '
                f'(Limit: <{cfg.cosine_threshold:.2f}). '
                f'Query matches denylist corpus.'
            )
        else:
            msg = (
                f'🛑 [FW] Segment violation: "{failed_clause}". '
                f'Cosine: {details.get("cosine_sim", 0):.3f} '
                f'(Required: >={cfg.cosine_threshold:.2f}). '
                f'Vector direction diverges from corpus.'
            )
    elif bare_reason == "noise":
        if negative:
            msg = (
                f'🛑 [FW]{mode_tag} Restricted content detected: "{failed_clause}". '
                f'Noise pre-filter: avg_delta={details.get("avg_delta", 0):.4f} '
                f'(Limit: {cfg.global_noise_limit:.3f}). '
                f'Query is too close to denylist corpus.'
            )
        else:
            msg = (
                f'🛑 [FW] Segment violation: "{failed_clause}". '
                f'Noise pre-filter: avg_delta={details.get("avg_delta", 0):.4f} '
                f'(Limit: {cfg.global_noise_limit:.3f}).'
            )
    elif bare_reason == "no_context":
        msg = (
            f'🛑 [FW] Segment violation: "{failed_clause}". '
            f'No context match in corpus.'
        )
    elif bare_reason == "excitation":
        adaptive_note = ""
        if details.get("adaptive_applied"):
            adaptive_note = f' [ADAPTIVE] Factor: {details.get("adaptive_factor", 1.0)}x.'
        if negative:
            msg = (
                f'🛑 [FW]{mode_tag} Restricted content detected: "{failed_clause}". '
                f'Resonance: {details.get("activations", 0)}/{details.get("threshold", 0):.0f}.{adaptive_note} '
                f'Query matches denylist corpus.'
            )
        else:
            msg = (
                f'🛑 [FW] Segment violation: "{failed_clause}". '
                f'Resonance: {details.get("activations", 0)}/{details.get("threshold", 0):.0f}.{adaptive_note}'
            )
    else:
        msg = (
            f'🛑 [FW]{mode_tag} Segment violation: "{failed_clause}". '
            f'Reason: {reason}.'
        )

    stage_summary = " → ".join(
        f'{r["stage"]}:{"OK" if r["passed"] else "BREACH"}' for r in traces
    )
    msg += f'\nPipeline: [{stage_summary}]'
    return msg

# --- System Stats Endpoint ---

@router.get("/system/stats", dependencies=[Depends(verify_api_key)])
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
    except Exception as e:
        logger.warning("GPU telemetry unavailable: %s", e)

    return {"cpu": cpu, "ram": ram, "gpu": gpu_percent}

# --- Health Check ---

@router.get("/health")
async def health_check():
    """Liveness/readiness probe for load balancers and orchestrators.
    Returns minimal info without auth; detailed info requires API key."""
    from datetime import datetime, timezone
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

# --- OpenAI-Compatible Transparent Proxy ---

@router.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
@limiter.limit(settings.rate_limit_chat)
async def openai_proxy(request: Request, config: OpenAIConfig):
    """Transparent proxy: OpenAI v1/chat/completions spec with firewall interception."""
    from app.core import state as state_mod
    from fastapi.responses import Response
    import uuid as _uuid
    cfg = state_mod.config_state

    # 1. Capture full message history for FPI
    request_history = [m.model_dump() for m in config.messages]
    last_msg = config.messages[-1].content
    clauses = SemanticFirewall.segment(last_msg)

    # 2. Firewall Evaluation
    fw_on = cfg.noise_enabled or cfg.cosine_enabled or cfg.excitation_enabled
    proxy_negative = cfg.firewall_mode == "negative"
    all_traces: list[dict] = []
    if fw_on:
        for clause in clauses:
            cl_vec = embedder.embed(clause)
            results = storage.search_nearest(cl_vec, k=cfg.rag_top_k)
            if not results:
                if proxy_negative:
                    # Negative mode: no corpus match → nothing to restrict → skip
                    all_traces.append({"stage": "no_context", "passed": True, "value": 0, "threshold": 0})
                    continue
                no_ctx_trace = [{"stage": "no_context", "passed": False, "value": 0, "threshold": 0}]
                emit_trace(
                    model=config.model,
                    last_message=last_msg,
                    decision="BREACH",
                    pipeline_trace=no_ctx_trace,
                    response_preview="",
                    request_history=request_history,
                    status="BREACH",
                )
                return Response(
                    content=json.dumps({
                        "error": {
                            "message": f"\ud83d\uded1 [FW] Segment violation: no context match for \"{clause}\"",
                            "type": "security_breach",
                            "code": "403"
                        }
                    }),
                    status_code=403,
                    media_type="application/json"
                )

            db_vec = results[0]["vector"]
            q_arr = np.array(cl_vec, dtype=np.float32)
            c_arr = np.array(db_vec, dtype=np.float32)
            word_count = len(clause.split())

            res = SemanticFirewall.evaluate_clause(q_arr, c_arr, cfg, word_count)
            all_traces.extend(res["trace"])
            if not res["passed"]:
                emit_trace(
                    model=config.model,
                    last_message=last_msg,
                    decision="BREACH",
                    pipeline_trace=all_traces,
                    response_preview="",
                    request_history=request_history,
                    status="BREACH",
                )
                return Response(
                    content=json.dumps({
                        "error": {
                            "message": f"\ud83d\uded1 [FW] Segment violation: {res['breach_reason']}",
                            "type": "security_breach",
                            "code": "403"
                        }
                    }),
                    status_code=403,
                    media_type="application/json"
                )

    # 3. Emit PASS trace with trace_id for stream correlation
    trace_id = str(_uuid.uuid4())
    if fw_on:
        emit_trace(
            trace_id=trace_id,
            model=config.model,
            last_message=last_msg,
            decision="PASS",
            pipeline_trace=all_traces,
            response_preview="[streaming]",
            request_history=request_history,
            status="PENDING",
        )

    # 4. Async Stream Wrapper — non-blocking token buffering for FPI
    async def stream_wrapper(gen, tid):
        """Pass-through generator that buffers response tokens for sniffer reconstruction."""
        full_content = []
        async for chunk in gen:
            # Extract content from SSE data line for buffering
            if chunk.startswith("data: ") and chunk.strip() != "data: [DONE]":
                try:
                    payload = json.loads(chunk[6:])
                    delta = payload.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        full_content.append(delta)
                except (json.JSONDecodeError, IndexError, KeyError):
                    pass
            yield chunk
        # Post-stream: fire-and-forget trace update with reconstructed response
        reconstructed = "".join(full_content)
        update_trace(tid, response_content=reconstructed, status="COMPLETED")

    # 5. Forward to Provider (wrapped for FPI)
    return StreamingResponse(
        stream_wrapper(
            provider.stream_chat(config.model, [m.model_dump() for m in config.messages]),
            trace_id,
        ),
        media_type="text/event-stream"
    )


# --- Real-Time Semantic Sniffer SSE Endpoint ---

@router.get("/v1/sniffer/stream", dependencies=[Depends(verify_api_key)])
async def sniffer_stream():
    """SSE endpoint for real-time firewall telemetry observation."""
    sub_q = await subscribe()
    async def event_generator():
        try:
            async for event in stream_sniffer_sse(sub_q):
                yield event
        finally:
            await unsubscribe(sub_q)
    return StreamingResponse(event_generator(), media_type="text/event-stream")
