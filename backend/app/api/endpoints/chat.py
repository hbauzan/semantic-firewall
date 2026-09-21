"""Chat Endpoints — /chat and /v1/chat/completions (OpenAI proxy).

Extracted from routes.py as part of Router Decomposition (Finding A1).
Key changes from the original:
  - stream_ollama() removed (Finding Q3): /chat now uses BaseProvider.stream_chat()
  - Provider instantiation is lazy (Finding A2): get_provider() called inside handlers
  - System prompt injection at endpoint level (per user decision Q2)
"""
import asyncio
import json
import logging
import math
import numpy as np
import uuid
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response, StreamingResponse

from app.modules.storage import storage
from app.modules.dispatcher import get_dispatcher
from app.modules.sniffer import emit_trace, update_trace, subscribe, unsubscribe, stream_sniffer_sse
from app.core.models import ConfigState, ChatRequest, OpenAIConfig
from app.core.firewall import SemanticFirewall
from app.core.exceptions import BurstDetectionBreach
from app.core.settings import settings
from app.modules.providers.ollama import OllamaProvider
from app.modules.providers.google import GoogleGeminiProvider
from app.modules.providers.openai import OpenAIProvider
from app.modules.providers.anthropic import AnthropicProvider
from app.modules.providers.groq import GroqProvider
from app.api.endpoints._shared import verify_api_key, limiter
from app.modules.persistence import persist_interaction
from app.modules.rag_context import accumulate_rag_chunks, join_rag_context
from app.modules.egress import EGRESS_CUT_MESSAGE, audit_chat_sentence, audit_held_response, redact_for_log
from app.modules.sentence_buffer import SentenceBuffer

logger = logging.getLogger(__name__)

router = APIRouter()


def _fmt_float(value: float) -> str:
    """Serialize a float with its full IEEE 754 mantissa.

    Telemetry is exported data, not decoration: a fixed-decimal rendering
    merges distinct vectors that differ only below the printed precision.
    """
    return f"{float(value):.17g}"


def _fmt_compact(value: float) -> str:
    """Human-facing rendering for values already floored to 3 decimals.

    ``str(float)`` yields the shortest round-tripping decimal, so a clean 0.653
    stays ``0.653`` instead of the ``:.17g`` mantissa dump. This is cosmetic
    text for the user, not exported vector data.
    """
    return str(float(value))


# --- Firewall helpers ---

def _enforce_raw_entropy(clause: str, cfg: ConfigState) -> None:
    """Phase 1: CPU-only burst detection before embedding."""
    if not cfg.noise_enabled:
        return
    entropy = SemanticFirewall.calculate_raw_entropy(clause)
    if entropy < cfg.raw_entropy_limit:
        logger.info(
            "SHORT_CIRCUIT layer=raw_entropy entropy=%.17g limit=%.17g",
            entropy, cfg.raw_entropy_limit,
        )
        raise BurstDetectionBreach(clause, entropy, cfg.raw_entropy_limit)


async def _embed_clause(clause: str, request: Request | None = None):
    """Route embedding through the unified inference dispatcher when available."""
    if request is not None and hasattr(request.app.state, "inference_dispatcher"):
        return await request.app.state.inference_dispatcher.submit_inference(clause)
    return await get_dispatcher().submit_inference(clause)


async def _evaluate_clauses(
    clauses: list[str],
    cfg: ConfigState,
    *,
    request: Request | None = None,
) -> tuple[list[str], set, int, str | None, str, dict, list, int, float]:
    """Shared firewall loop for /chat and /v1/chat/completions."""
    context_chunks: list[str] = []
    seen_chunk_ids: set = set()
    clauses_with_hits = 0
    failed_clause = None
    block_reason = ""
    block_details: dict = {}
    all_traces: list[dict] = []
    last_activations = 0
    last_cosine = 0.0
    negative = cfg.firewall_mode == "negative"

    for clause in clauses:
        _enforce_raw_entropy(clause, cfg)
        embedding = await _embed_clause(clause, request)
        cl_vec = embedding.dense
        results = storage.search_for_firewall(
            cl_vec, k=cfg.rag_top_k, active_corpus_file=cfg.active_corpus_file,
        )
        if not results:
            if negative:
                all_traces.append({"stage": "no_context", "passed": True})
                continue
            failed_clause = clause
            block_reason = "no_context"
            block_details = {"clause": clause}
            all_traces.append({"stage": "no_context", "passed": False})
            break

        clauses_with_hits += 1
        accumulate_rag_chunks(results, context_chunks, seen_chunk_ids)
        db_vec = results[0]["vector"]
        q_arr = np.array(cl_vec, dtype=np.float64)
        c_arr = np.array(db_vec, dtype=np.float64)
        word_count = len(clause.split())
        c_sparse = results[0].get("sparse_lexical")

        result = SemanticFirewall.evaluate_clause(
            q_arr,
            c_arr,
            cfg,
            word_count,
            query_text=clause,
            q_sparse=embedding.sparse,
            c_sparse=c_sparse,
        )
        all_traces.extend(result["trace"])
        last_activations = result["last_activations"]
        last_cosine = result["last_cosine"]

        if not result["passed"]:
            failed_clause = clause
            block_reason = result["breach_reason"]
            block_details = result["breach_details"] or {}
            if results:
                # last_cosine already carries this clause's exact float64 score,
                # computed against the very same top-1 vector c_arr was built from.
                block_details["top_hit_text"] = results[0].get("text", "")
                block_details["top_hit_score"] = last_cosine
            break

    return (
        context_chunks,
        seen_chunk_ids,
        clauses_with_hits,
        failed_clause,
        block_reason,
        block_details,
        all_traces,
        last_activations,
        last_cosine,
    )


def _burst_block_details(exc: BurstDetectionBreach) -> dict:
    return {
        "entropy": exc.entropy,
        "limit": exc.limit,
        "breach_type": exc.breach_type,
    }

# --- Provider Abstraction (Lazy Init — Finding A2) ---

def get_provider(cfg: ConfigState):
    """Resolve provider at call time to prevent boot-time crashes if keys are missing."""
    provider_name = cfg.upstream_provider
    if provider_name == "google":
        if not settings.google_key_value:
            logger.critical("UPSTREAM_PROVIDER set to 'google' but GOOGLE_API_KEY is missing.")
            raise RuntimeError("Missing Google API Key")
        return GoogleGeminiProvider(), settings.gemini_model_id
    elif provider_name == "openai":
        if not settings.openai_key_value:
            logger.critical("UPSTREAM_PROVIDER set to 'openai' but OPENAI_API_KEY is missing.")
            raise RuntimeError("Missing OpenAI API Key")
        return OpenAIProvider(), settings.openai_model
    elif provider_name == "anthropic":
        if not settings.anthropic_key_value:
            logger.critical("UPSTREAM_PROVIDER set to 'anthropic' but ANTHROPIC_API_KEY is missing.")
            raise RuntimeError("Missing Anthropic API Key")
        return AnthropicProvider(), settings.anthropic_model
    elif provider_name == "groq":
        if not settings.groq_key_value:
            logger.critical("UPSTREAM_PROVIDER set to 'groq' but GROQ_API_KEY is missing.")
            raise RuntimeError("Missing Groq API Key")
        return GroqProvider(), settings.groq_model
    return OllamaProvider(), settings.ollama_model


# --- Chat Endpoint (Firewall Gateway) ---

@router.post("/chat", dependencies=[Depends(verify_api_key)])
@limiter.limit(settings.rate_limit_chat)
async def chat_endpoint(request: Request, req: ChatRequest):
    from app.core import state as state_mod
    cfg = state_mod.config_state  # immutable snapshot — consistent for entire request
    prompt = req.prompt
    fw_on = cfg.noise_enabled or cfg.cosine_enabled or cfg.excitation_enabled
    clean_prompt = prompt.strip()

    clauses = SemanticFirewall.segment(clean_prompt)

    context_chunks: list[str] = []
    seen_chunk_ids: set = set()
    clauses_with_hits = 0
    failed_clause = None
    block_reason = ""
    block_details: dict = {}
    all_traces: list[dict] = []
    last_activations = 0
    last_cosine = 0.0

    if fw_on:
        try:
            (
                context_chunks,
                seen_chunk_ids,
                clauses_with_hits,
                failed_clause,
                block_reason,
                block_details,
                all_traces,
                last_activations,
                last_cosine,
            ) = await _evaluate_clauses(clauses, cfg, request=request)
        except BurstDetectionBreach as exc:
            failed_clause = exc.clause
            block_reason = "BURST_DETECTION_BREACH"
            block_details = _burst_block_details(exc)
            all_traces = [{
                "stage": "raw_entropy",
                "passed": False,
                **block_details,
            }]
    else:
        for clause in clauses:
            embedding = await _embed_clause(clause, request)
            results = storage.search_for_firewall(
                embedding.dense, k=cfg.rag_top_k, active_corpus_file=cfg.active_corpus_file,
            )
            if results:
                clauses_with_hits += 1
                accumulate_rag_chunks(results, context_chunks, seen_chunk_ids)

    context = join_rag_context(context_chunks)
    rag_chunk_count = len(context_chunks)

    # --- Telemetry Formatting & Response ---
    if fw_on:
        provider, model_id = get_provider(cfg)
        
        if failed_clause is not None:
            all_traces.extend([
                {
                    "stage": "noise_tolerance",
                    "passed": True,
                    "value": cfg.noise_tolerance,
                    "threshold": cfg.noise_tolerance,
                },
                {
                    "stage": "adaptive",
                    "passed": True,
                    "value": cfg.adaptive_factor,
                    "threshold": cfg.adaptive_factor,
                },
            ])
            # NEW: Emit BREACH trace to Sniffer for UI parity
            emit_trace(
                model=model_id,
                last_message=prompt,
                decision="BREACH",
                pipeline_trace=all_traces,
                request_history=[{"role": "user", "content": prompt}],
                status="BREACH"
            )
            
            block_msg = _format_block_message(
                failed_clause, block_reason, block_details, cfg, all_traces
            )
            async def breach_stream():
                yield json.dumps({"type": "content", "text": block_msg}).encode("utf-8") + b"\n"
            return StreamingResponse(breach_stream(), media_type="application/x-ndjson")

        entropy = 0.0
        for t in all_traces:
            if t.get("stage") == "noise":
                entropy = t.get("entropy", t.get("value", 0.0))
                break

        all_traces.extend([
            {
                "stage": "rag_context",
                "passed": True,
                "chunk_count": rag_chunk_count,
                "k": cfg.rag_top_k,
                "clauses_with_hits": clauses_with_hits,
            },
            {
                "stage": "noise_tolerance",
                "passed": True,
                "value": cfg.noise_tolerance,
                "threshold": cfg.noise_tolerance,
            },
            {
                "stage": "adaptive",
                "passed": True,
                "value": cfg.adaptive_factor,
                "threshold": cfg.adaptive_factor,
            },
        ])

        trace_id = emit_trace(
            model=model_id,
            last_message=req.prompt,
            decision="PASS",
            pipeline_trace=all_traces,
            request_history=[{"role": "user", "content": req.prompt}],
            status="PENDING"
        )
        
        telemetry_block = (
            f"[FIREWALL_AUDIT]\n"
            f"[FW_PASS]\n"
            f"Engine: {cfg.upstream_provider.upper()} | {model_id}\n"
            f"Mode: {cfg.firewall_mode.upper()}\n"
            f"Metrics: Entropy({_fmt_float(entropy)} / Limit: {_fmt_float(cfg.global_noise_limit)}) | "
            f"Cosine({_fmt_float(last_cosine)} / Limit: {_fmt_float(cfg.cosine_threshold)}) | "
            f"Excitation({last_activations} / Limit: {cfg.excitation_threshold}) | "
            f"Noise Tolerance({_fmt_float(cfg.noise_tolerance)}) | "
            f"Adaptive({_fmt_float(cfg.adaptive_factor)}) | "
            f"RAG Context({rag_chunk_count} chunks, k={cfg.rag_top_k})\n"
            f"RAG: {rag_chunk_count} chunks injected "
            f"(k={cfg.rag_top_k}, clauses={clauses_with_hits}, unique={rag_chunk_count})\n"
            f"{'-' * 40}\n"
            f"[LLM_RESPONSE]:\n\n"
        )
        
        async def ui_stream_wrapper():
            yield json.dumps({"response": telemetry_block}).encode("utf-8") + b"\n"
            try:
                if cfg.egress_profile == "compliance":
                    reconstructed = await _absorb_ndjson(
                        _stream_via_provider(clean_prompt, context, cfg, strict=True)
                    )
                    ok, payload, log_text = _gate_generation(reconstructed, cfg)
                    yield json.dumps({"response": payload}).encode("utf-8") + b"\n"
                else:
                    ok, reconstructed, log_text = True, "", ""
                    async for item in _gated_chat_ndjson(
                        _stream_via_provider(clean_prompt, context, cfg, strict=True),
                        cfg,
                    ):
                        if item[0] == "chunk":
                            yield item[1]
                        else:
                            ok, reconstructed, log_text = item[1]
            except Exception as e:
                err = _llm_error_text(e)
                yield json.dumps({"response": err}).encode("utf-8") + b"\n"
                update_trace(trace_id, status="ERROR", response_content=err)
                return

            update_trace(
                trace_id,
                response_content=log_text,
                status="COMPLETED" if ok else "EGRESS_BREACH",
            )
            await asyncio.to_thread(persist_interaction, clean_prompt, log_text)

        return StreamingResponse(ui_stream_wrapper(), media_type="application/x-ndjson")

    async def no_fw_stream_wrapper():
        try:
            if cfg.egress_profile == "compliance":
                reconstructed = await _absorb_ndjson(_stream_via_provider(clean_prompt, context, cfg))
                _ok, payload, log_text = _gate_generation(reconstructed, cfg)
                yield json.dumps({"response": payload}).encode("utf-8") + b"\n"
            else:
                log_text = ""
                async for item in _gated_chat_ndjson(
                    _stream_via_provider(clean_prompt, context, cfg),
                    cfg,
                ):
                    if item[0] == "chunk":
                        yield item[1]
                    else:
                        log_text = item[1][2]
        except Exception as e:
            yield json.dumps({"response": _llm_error_text(e)}).encode("utf-8") + b"\n"
            return

        await asyncio.to_thread(persist_interaction, clean_prompt, log_text)

    return StreamingResponse(
        no_fw_stream_wrapper(), media_type="application/x-ndjson"
    )


def _llm_error_text(e: Exception) -> str:
    """Client-facing message when the upstream LLM is unreachable mid-stream."""
    return (
        f"🔴 [LLM_ERROR] Cannot reach the language model. "
        f"Ensure the inference server is running. {e}"
    )


def _delta_from_ndjson_chunk(chunk: bytes) -> str:
    try:
        line = chunk.decode("utf-8").strip()
        if not line:
            return ""
        payload = json.loads(line)
        return str(payload.get("response", "") or "")
    except Exception:
        return ""


def _delta_from_sse_line(chunk: str) -> str:
    if not chunk.startswith("data: ") or chunk.strip() == "data: [DONE]":
        return ""
    try:
        payload = json.loads(chunk[6:])
        return str(payload.get("choices", [{}])[0].get("delta", {}).get("content", "") or "")
    except (json.JSONDecodeError, IndexError, KeyError, TypeError):
        return ""


async def _absorb_ndjson(agen) -> str:
    parts: list[str] = []
    async for chunk in agen:
        delta = _delta_from_ndjson_chunk(chunk)
        if delta:
            parts.append(delta)
    return "".join(parts)


async def _absorb_sse(agen) -> str:
    parts: list[str] = []
    async for chunk in agen:
        delta = _delta_from_sse_line(chunk)
        if delta:
            parts.append(delta)
    return "".join(parts)


def _gate_generation(reconstructed: str, cfg: ConfigState) -> tuple[bool, str, str]:
    """Return (passed, client_payload, log_payload). Only the compliance hold."""
    log_text = redact_for_log(reconstructed)
    if cfg.egress_profile != "compliance":
        return True, reconstructed, log_text
    verdict = audit_held_response(reconstructed, pack_id=cfg.active_corpus_file)
    if verdict.passed:
        return True, reconstructed, log_text
    logger.info("egress hold cut layer=%s reason=%s", verdict.layer, verdict.reason)
    return False, EGRESS_CUT_MESSAGE, log_text


async def _gated_chat_ndjson(agen, cfg: ConfigState):
    """Yield NDJSON sentence bursts; final item is ('done', (ok, delivered, log))."""
    buffer = SentenceBuffer()
    parts: list[str] = []
    cut = False
    async for chunk in agen:
        delta = _delta_from_ndjson_chunk(chunk)
        if not delta:
            continue
        for sentence in buffer.push(delta):
            verdict = audit_chat_sentence(sentence, pack_id=cfg.active_corpus_file)
            if not verdict.passed:
                cut = True
                break
            parts.append(sentence)
            yield ("chunk", json.dumps({"response": sentence}).encode("utf-8") + b"\n")
        if cut:
            break
    if not cut:
        tail = buffer.flush_tail()
        if tail:
            verdict = audit_chat_sentence(tail, pack_id=cfg.active_corpus_file)
            if verdict.passed:
                parts.append(tail)
                yield ("chunk", json.dumps({"response": tail}).encode("utf-8") + b"\n")
            else:
                cut = True
    delivered = "".join(parts)
    if cut:
        yield ("chunk", json.dumps({"response": EGRESS_CUT_MESSAGE}).encode("utf-8") + b"\n")
    yield ("done", (not cut, delivered, redact_for_log(delivered)))


async def _gated_chat_sse(agen, cfg: ConfigState):
    """Yield OpenAI SSE sentence bursts; final item is ('done', (ok, delivered, log))."""
    buffer = SentenceBuffer()
    parts: list[str] = []
    cut = False
    async for chunk in agen:
        delta = _delta_from_sse_line(chunk)
        if not delta:
            continue
        for sentence in buffer.push(delta):
            verdict = audit_chat_sentence(sentence, pack_id=cfg.active_corpus_file)
            if not verdict.passed:
                cut = True
                break
            parts.append(sentence)
            payload = {"choices": [{"delta": {"content": sentence}}]}
            yield ("chunk", f"data: {json.dumps(payload)}\n\n")
        if cut:
            break
    if not cut:
        tail = buffer.flush_tail()
        if tail:
            verdict = audit_chat_sentence(tail, pack_id=cfg.active_corpus_file)
            if verdict.passed:
                parts.append(tail)
                payload = {"choices": [{"delta": {"content": tail}}]}
                yield ("chunk", f"data: {json.dumps(payload)}\n\n")
            else:
                cut = True
    delivered = "".join(parts)
    if cut:
        err = {
            "error": {
                "message": "[FW_BLOCK] egress sentence",
                "type": "security_breach",
                "code": "403",
                "breach_type": "EGRESS_SENTENCE",
            }
        }
        yield ("chunk", f"data: {json.dumps(err)}\n\n")
    yield ("chunk", "data: [DONE]\n\n")
    yield ("done", (not cut, delivered, redact_for_log(delivered)))


async def _stream_via_provider(prompt: str, context: str, cfg: ConfigState, strict: bool = False):
    """Unified streaming via BaseProvider (replaces stream_ollama — Finding Q3).

    Constructs a messages array with optional strict system prompt, calls
    provider.stream_chat(), and converts SSE output to NDJSON for /chat compat.
    """
    messages = []

    if strict:
        messages.append({
            "role": "system",
            "content": (
                "You are a technical assistant. "
                "Base your response PRIMARILY on the provided context. "
                "If the user asks a question that has NO relation to the context "
                "(e.g. recipes, jokes, completely unrelated topics), "
                "briefly state you cannot help with that specific part, "
                "but DO answer the parts that relate to the context."
            ),
        })

    if context:
        messages.append({"role": "user", "content": f"Context:\n{context}\n\nUser query:\n{prompt}"})
    else:
        messages.append({"role": "user", "content": prompt})

    provider, model_id = get_provider(cfg)
    try:
        async for sse_line in provider.stream_chat(model_id, messages):
            # SSE format: "data: {...}\n\n" — extract content for NDJSON conversion
            if sse_line.startswith("data: ") and sse_line.strip() != "data: [DONE]":
                try:
                    payload = json.loads(sse_line[6:])
                    delta = payload.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if delta:
                        yield json.dumps({"response": delta}).encode("utf-8") + b"\n"
                except (json.JSONDecodeError, IndexError, KeyError):
                    pass
    except Exception as e:
        logger.error("Provider connection failed: %s", e)
        raise


def _format_block_message(
    failed_clause: str, reason: str, details: dict, cfg: ConfigState, traces: list
) -> str:
    """Format the telemetry block message based on which filter breached."""
    negative = cfg.firewall_mode == "negative"
    mode_tag = " [NEGATIVE]" if negative else ""

    header = f"[FIREWALL_AUDIT]\n[FW_BLOCK]{mode_tag}"

    cos_trace = next((t for t in traces if t.get("stage") == "cosine"), None)
    exc_trace = next((t for t in traces if t.get("stage") == "excitation"), None)
    noise_trace = next((t for t in traces if t.get("stage") == "noise"), None)

    metric_parts = []
    if cos_trace:
        val = cos_trace.get("cosine_sim", 0.0)
        req = cfg.cosine_threshold
        st = "OK" if cos_trace.get("passed", False) else "FAIL"
        metric_parts.append(f"Cosine({_fmt_float(val)} / Limit: {_fmt_float(req)}) [{st}]")

    if exc_trace:
        act = exc_trace.get("activations", 0)
        thr = exc_trace.get("threshold", 0)
        st = "OK" if exc_trace.get("passed", False) else "FAIL"
        adaptive_applied = exc_trace.get("adaptive_applied", False)
        factor = exc_trace.get("adaptive_factor", 1.0)
        base_thr = cfg.excitation_threshold
        if adaptive_applied and factor != 1.0:
            exc_desc = (
                f"Excitation({act} / Limit: {_fmt_float(thr)} "
                f"[Adaptive {_fmt_float(factor)}x: Base {base_thr} -> {_fmt_float(thr)}]) [{st}]"
            )
        else:
            exc_desc = f"Excitation({act} / Limit: {_fmt_float(thr)}) [{st}]"
        metric_parts.append(exc_desc)

    if noise_trace:
        ent = noise_trace.get("entropy", 0.0)
        limit = cfg.global_noise_limit
        st = "OK" if noise_trace.get("passed", False) else "FAIL"
        metric_parts.append(f"Entropy({_fmt_float(ent)} / Limit: {_fmt_float(limit)}) [{st}]")

    if metric_parts:
        metric_line = f"Metrics: {' | '.join(metric_parts)}"
    else:
        metric_line = (
            f"Reason: {reason} | Noise Tolerance({_fmt_float(cfg.noise_tolerance)}) "
            f"| Adaptive({_fmt_float(cfg.adaptive_factor)})"
        )

    # Tuning hints for manual calibration. Cosmetic user text: the 3-decimal
    # floor is the whole point, so it is rendered compactly, not as raw mantissa.
    tuning_targets = []
    if cos_trace:
        c_val = cos_trace.get("cosine_sim", 0.0)
        rec_cos = math.floor(c_val * 1000.0) / 1000.0
        tuning_targets.append(f"Cosine <= {_fmt_compact(rec_cos)}")
    if exc_trace:
        act = exc_trace.get("activations", 0)
        factor = exc_trace.get("adaptive_factor", 1.0)
        rec_exc = int(math.floor(act / factor)) if (exc_trace.get("adaptive_applied") and factor > 0) else act
        tuning_targets.append(f"Excitation <= {rec_exc}")
    if noise_trace:
        ent = noise_trace.get("entropy", 0.0)
        rec_noise = math.floor(ent * 1000.0) / 1000.0
        tuning_targets.append(f"Noise <= {_fmt_compact(rec_noise)}")

    hint_line = f"[TUNING HINT] To PASS: {', '.join(tuning_targets)}" if tuning_targets else ""

    top_hit_text = details.get("top_hit_text", "")
    top_hit_score = details.get("top_hit_score", 0.0)
    rag_match_line = ""
    if top_hit_text:
        snippet = top_hit_text.strip().replace("\n", " ")
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        score_fmt = _fmt_float(top_hit_score) if top_hit_score else "N/A"
        rag_match_line = f"RAG Match ({score_fmt}): \"{snippet}\""

    pipeline = " -> ".join([f"{r['stage']}:{'OK' if r['passed'] else 'FAIL'}" for r in traces])

    lines = [
        header,
        f"Mode: {cfg.firewall_mode.upper()}",
        f"Segment: \"{failed_clause}\"",
        metric_line,
    ]
    if hint_line:
        lines.append(hint_line)
    if rag_match_line:
        lines.append(rag_match_line)
    lines.extend([
        f"Pipeline: [{pipeline}]",
        "-" * 40,
        "[CONNECTION_TERMINATED]\n\n"
    ])

    return "\n".join(lines)


# --- OpenAI-Compatible Transparent Proxy ---

@router.post("/v1/chat/completions", dependencies=[Depends(verify_api_key)])
@limiter.limit(settings.rate_limit_chat)
async def openai_proxy(request: Request, config: OpenAIConfig):
    """Transparent proxy: OpenAI v1/chat/completions spec with firewall interception."""
    from app.core import state as state_mod
    from fastapi.responses import Response
    cfg = state_mod.config_state

    request_history = [m.model_dump() for m in config.messages]
    last_msg = config.messages[-1].content
    clauses = SemanticFirewall.segment(last_msg)

    fw_on = cfg.noise_enabled or cfg.cosine_enabled or cfg.excitation_enabled
    all_traces: list[dict] = []
    if fw_on:
        try:
            (
                _context_chunks,
                _seen,
                _clauses_with_hits,
                failed_clause,
                block_reason,
                block_details,
                all_traces,
                _last_act,
                _last_cos,
            ) = await _evaluate_clauses(clauses, cfg, request=request)
            if failed_clause is not None:
                emit_trace(
                    model=config.model,
                    last_message=last_msg,
                    decision="BREACH",
                    pipeline_trace=all_traces,
                    response_preview="",
                    request_history=request_history,
                    status="BREACH",
                )
                message = (
                    f"[FW_BLOCK] Segment violation: {block_reason}"
                    if block_reason != "BURST_DETECTION_BREACH"
                    else f"[FW_BLOCK] Burst detection breach on \"{failed_clause}\""
                )
                return Response(
                    content=json.dumps({
                        "error": {
                            "message": message,
                            "type": "security_breach",
                            "code": "403",
                            "breach_type": block_reason,
                        }
                    }),
                    status_code=403,
                    media_type="application/json",
                )
        except BurstDetectionBreach as exc:
            breach_trace = [{
                "stage": "raw_entropy",
                "passed": False,
                **_burst_block_details(exc),
            }]
            emit_trace(
                model=config.model,
                last_message=last_msg,
                decision="BREACH",
                pipeline_trace=breach_trace,
                response_preview="",
                request_history=request_history,
                status="BREACH",
            )
            return Response(
                content=json.dumps({
                    "error": {
                        "message": f"[FW_BLOCK] Burst detection breach on \"{exc.clause}\"",
                        "type": "security_breach",
                        "code": "403",
                        "breach_type": "BURST_DETECTION_BREACH",
                    }
                }),
                status_code=403,
                media_type="application/json",
            )

    # 3. Emit PASS trace with trace_id for stream correlation
    trace_id = str(uuid.uuid4())
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
    provider, _ = get_provider(cfg)
    gen = provider.stream_chat(config.model, [m.model_dump() for m in config.messages])
    tid = trace_id if fw_on else None

    if cfg.egress_profile == "compliance":
        try:
            reconstructed = await _absorb_sse(gen)
        except Exception as e:
            logger.error("Proxy upstream connection failed: %s", e)
            if tid:
                update_trace(tid, status="ERROR", response_content=_llm_error_text(e))
            return Response(
                content=json.dumps({
                    "error": {
                        "message": _llm_error_text(e),
                        "type": "upstream_error",
                        "code": "502",
                    }
                }),
                status_code=502,
                media_type="application/json",
            )
        ok, payload, log_text = _gate_generation(reconstructed, cfg)
        if tid:
            update_trace(
                tid,
                response_content=log_text,
                status="COMPLETED" if ok else "EGRESS_BREACH",
            )
        await asyncio.to_thread(persist_interaction, last_msg, log_text)
        if not ok:
            return Response(
                content=json.dumps({
                    "error": {
                        "message": "[FW_BLOCK] egress hold",
                        "type": "security_breach",
                        "code": "403",
                        "breach_type": "EGRESS_HOLD",
                    }
                }),
                status_code=403,
                media_type="application/json",
            )

        async def burst():
            yield f"data: {json.dumps({'choices': [{'delta': {'content': payload}}]})}\n\n"
            yield "data: [DONE]\n\n"

        return StreamingResponse(burst(), media_type="text/event-stream")

    async def stream_wrapper(upstream, trace_id_for_update):
        """Chat profile: freeze on `. ; ? \\n`, eval, burst or abort."""
        try:
            ok, reconstructed, log_text = True, "", ""
            async for item in _gated_chat_sse(upstream, cfg):
                if item[0] == "chunk":
                    yield item[1]
                else:
                    ok, reconstructed, log_text = item[1]
        except Exception as e:
            logger.error("Proxy upstream connection failed: %s", e)
            if trace_id_for_update:
                update_trace(trace_id_for_update, status="ERROR", response_content=_llm_error_text(e))
            err_payload = {
                "error": {
                    "message": _llm_error_text(e),
                    "type": "upstream_error",
                    "code": "502",
                }
            }
            yield f"data: {json.dumps(err_payload)}\n\n"
            yield "data: [DONE]\n\n"
            return
        if trace_id_for_update:
            update_trace(
                trace_id_for_update,
                response_content=log_text,
                status="COMPLETED" if ok else "EGRESS_BREACH",
            )
        await asyncio.to_thread(persist_interaction, last_msg, log_text)

    return StreamingResponse(
        stream_wrapper(gen, tid),
        media_type="text/event-stream"
    )

# --- History Routes ---

@router.get("/chat/history", dependencies=[Depends(verify_api_key)])
async def get_chat_history():
    from app.modules.persistence import load_chat_history
    history = await asyncio.to_thread(load_chat_history)
    return history

@router.delete("/chat/history", dependencies=[Depends(verify_api_key)])
async def delete_chat_history():
    from app.modules.persistence import save_chat_history
    await asyncio.to_thread(save_chat_history, [])
    return {"status": "cleared"}
