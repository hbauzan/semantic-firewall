"""Real-Time Semantic Sniffer (RTSS) — zero-latency observability layer.

Producer-Consumer pattern using asyncio.Queue:
  - emit_trace()   → fire-and-forget into sniffer_queue (never blocks proxy)
  - sniffer_consumer() → background task that broadcasts to SSE subscribers
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import AsyncGenerator, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SnifferTrace Schema
# ---------------------------------------------------------------------------


class PipelineStageTrace(BaseModel):
    stage: str          # "noise" | "cosine" | "excitation"
    passed: bool
    value: float
    threshold: float


class SnifferTraceRequest(BaseModel):
    model: str
    last_message: str
    request_history: list[dict] = Field(default_factory=list)


class SnifferTraceFirewall(BaseModel):
    decision: str       # "PASS" | "BREACH"
    pipeline_trace: list[PipelineStageTrace]


class SnifferTrace(BaseModel):
    id: str
    timestamp: str
    request: SnifferTraceRequest
    firewall: SnifferTraceFirewall
    response_preview: str
    response_content: str = ""
    status: str = "PENDING"  # PENDING → COMPLETED | BREACH


# ---------------------------------------------------------------------------
# Global Queue & Subscriber Registry
# ---------------------------------------------------------------------------

sniffer_queue: asyncio.Queue[SnifferTrace] = asyncio.Queue(maxsize=256)

# Connected SSE clients — each gets its own queue
_subscribers: set[asyncio.Queue[SnifferTrace]] = set()
_subscribers_lock = asyncio.Lock()

# Circular buffer of recent traces (for late-joining clients).
# THREAD-SAFETY NOTE: _trace_buffer is accessed exclusively from the asyncio
# event loop — the consumer task (writer), update_trace() (writer), and
# stream_sniffer_sse() generators (readers) all execute in the same loop.
# This is safe under asyncio's cooperative scheduling (no preemption between
# awaits within a single task). Do NOT access from threads — if a threaded
# consumer is ever introduced, replace with threading.Lock or asyncio.Lock.
_trace_buffer: list[SnifferTrace] = []
_BUFFER_MAX = 100


# ---------------------------------------------------------------------------
# Producer API  (called from routes — never awaited by the proxy stream)
# ---------------------------------------------------------------------------

def emit_trace(
    *,
    trace_id: Optional[str] = None,
    model: str,
    last_message: str,
    decision: str,
    pipeline_trace: list[dict],
    response_preview: str = "",
    request_history: Optional[list[dict]] = None,
    status: Optional[str] = None,
) -> str:
    """Build a SnifferTrace and fire-and-forget into the queue.

    Uses put_nowait so the proxy stream is NEVER blocked.
    If the queue is full, the trace is dropped with a warning.
    Returns the trace_id for correlation with post-stream updates.
    """
    stages = []
    for t in pipeline_trace:
        # Extract numeric value depending on stage type
        value = 0.0
        threshold = 0.0
        stage_name = t.get("stage", "unknown")
        if stage_name == "noise":
            value = t.get("avg_delta", 0.0)
            threshold = t.get("limit", t.get("global_noise_limit", 0.0))
        elif stage_name == "cosine":
            value = t.get("cosine_sim", 0.0)
            threshold = t.get("cosine_threshold", 0.0)
        elif stage_name == "excitation":
            value = float(t.get("activations", 0))
            threshold = float(t.get("threshold", 0))
        elif stage_name == "no_context":
            # Corpus is empty or returned no results — no numeric metric applies.
            # value=0 / threshold=0 signals absence of context rather than a
            # filter measurement. Frontend should display this as a corpus miss,
            # not as a threshold comparison.
            value = 0.0
            threshold = 0.0
        stages.append(PipelineStageTrace(
            stage=stage_name,
            passed=t.get("passed", False),
            value=value,
            threshold=threshold,
        ))

    tid = trace_id or str(uuid.uuid4())
    resolved_status = status or ("BREACH" if decision == "BREACH" else "PENDING")

    trace = SnifferTrace(
        id=tid,
        timestamp=datetime.now(timezone.utc).isoformat(),
        request=SnifferTraceRequest(
            model=model,
            last_message=last_message[:200],
            request_history=request_history or [],
        ),
        firewall=SnifferTraceFirewall(decision=decision, pipeline_trace=stages),
        response_preview=response_preview[:100],
        response_content="",
        status=resolved_status,
    )

    try:
        sniffer_queue.put_nowait(trace)
    except asyncio.QueueFull:
        logger.warning("Sniffer queue full — dropping trace %s", trace.id)

    return tid


def update_trace(
    trace_id: str,
    *,
    response_content: str = "",
    status: str = "COMPLETED",
) -> None:
    """Post-stream update: append reconstructed response to an existing trace.

    Scans the circular buffer for the matching trace_id, mutates in-place,
    and pushes the updated trace back through the queue so SSE subscribers
    receive the completed payload.
    """
    updated_trace: Optional[SnifferTrace] = None
    for i, t in enumerate(_trace_buffer):
        if t.id == trace_id:
            # Pydantic frozen model — rebuild with updated fields
            updated = t.model_copy(update={
                "response_content": response_content,
                "status": status,
            })
            _trace_buffer[i] = updated
            updated_trace = updated
            break

    if updated_trace is None:
        logger.warning("update_trace: trace_id %s not found in buffer", trace_id)
        return

    try:
        sniffer_queue.put_nowait(updated_trace)
    except asyncio.QueueFull:
        logger.warning("Sniffer queue full — dropping trace update %s", trace_id)


# ---------------------------------------------------------------------------
# Consumer — background asyncio.Task
# ---------------------------------------------------------------------------

_consumer_task: asyncio.Task | None = None


async def sniffer_consumer() -> None:
    """Read traces from the queue, buffer them, and broadcast to SSE subscribers."""
    logger.info("RTSS consumer started")
    while True:
        try:
            trace = await sniffer_queue.get()
        except asyncio.CancelledError:
            logger.info("RTSS consumer shutting down")
            return

        # Append to circular buffer
        _trace_buffer.append(trace)
        if len(_trace_buffer) > _BUFFER_MAX:
            _trace_buffer.pop(0)

        # Broadcast to all subscribers
        async with _subscribers_lock:
            dead: list[asyncio.Queue] = []
            for sub_q in _subscribers:
                try:
                    sub_q.put_nowait(trace)
                except asyncio.QueueFull:
                    dead.append(sub_q)
            for d in dead:
                _subscribers.discard(d)


def start_consumer() -> None:
    """Spawn the consumer as a background task on the running event loop.

    Must be called from within an async context (e.g. FastAPI lifespan) where
    a running event loop already exists. Uses asyncio.create_task() — the
    modern Python 3.10+ approach that avoids the DeprecationWarning emitted
    by asyncio.get_event_loop() when called outside an async context.
    """
    global _consumer_task
    _consumer_task = asyncio.create_task(sniffer_consumer())


def stop_consumer() -> None:
    """Cancel the consumer task gracefully."""
    global _consumer_task
    if _consumer_task:
        _consumer_task.cancel()
        _consumer_task = None


# ---------------------------------------------------------------------------
# SSE Subscriber Management
# ---------------------------------------------------------------------------

async def subscribe() -> asyncio.Queue[SnifferTrace]:
    """Register a new SSE client and return its subscriber queue."""
    q: asyncio.Queue[SnifferTrace] = asyncio.Queue(maxsize=128)
    async with _subscribers_lock:
        _subscribers.add(q)
    logger.info("Sniffer SSE client connected (%d total)", len(_subscribers))
    return q


async def unsubscribe(q: asyncio.Queue[SnifferTrace]) -> None:
    """Remove an SSE client's subscriber queue."""
    async with _subscribers_lock:
        _subscribers.discard(q)
    logger.info("Sniffer SSE client disconnected (%d remaining)", len(_subscribers))


async def stream_sniffer_sse(q: asyncio.Queue[SnifferTrace]) -> AsyncGenerator[str, None]:
    """Async generator yielding SSE-formatted events for a subscriber."""
    try:
        while True:
            try:
                trace = await asyncio.wait_for(q.get(), timeout=30.0)
                yield f"data: {trace.model_dump_json()}\n\n"
            except asyncio.TimeoutError:
                # SSE keep-alive to prevent proxy/browser timeout
                yield ": heartbeat\n\n"
    except asyncio.CancelledError:
        return
