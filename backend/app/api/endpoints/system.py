"""System Endpoints — health, stats, sniffer stream.

Extracted from routes.py as part of Router Decomposition (Finding A1).
"""
import logging
import psutil
import torch
from fastapi import APIRouter, Depends

from app.modules.sniffer import subscribe, unsubscribe, stream_sniffer_sse, get_sniffer_history, clear_history_backend
from app.api.endpoints._shared import verify_api_key
from fastapi.responses import StreamingResponse

logger = logging.getLogger(__name__)

router = APIRouter()

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

# --- Real-Time Semantic Sniffer SSE Endpoint ---

@router.get("/v1/sniffer/stream", dependencies=[Depends(verify_api_key)])
async def sniffer_stream():
    """SSE endpoint for real-time firewall telemetry observation."""
    from app.core import state as state_mod
    limit = state_mod.config_state.sniffer_view_limit

    sub_q = await subscribe()
    async def event_generator():
        try:
            async for event in stream_sniffer_sse(sub_q, limit):
                yield event
        finally:
            await unsubscribe(sub_q)
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/system/logs/export", dependencies=[Depends(verify_api_key)])
async def export_forensic_logs():
    """Aggregates all in-memory sniffer traces for forensic audit."""
    history = get_sniffer_history()
    return {
        "export_version": "v2.30.0",
        "total_traces": len(history),
        "traces": [t.model_dump() for t in history]
    }

@router.delete("/system/sniffer/history", dependencies=[Depends(verify_api_key)])
async def clear_sniffer_history():
    """Wipes the forensic sniffer history completely."""
    await clear_history_backend()
    return {"status": "cleared"}
