"""L07 — compliance egress hold. Ingress evaluate_clause is unchanged."""
from __future__ import annotations

import httpx
import pytest

from app.core.state import set_config_sync as set_config
from app.main import app
from app.modules.egress import (
    EGRESS_CUT_MESSAGE,
    audit_held_response,
    normalize_homoglyphs,
    reconstruct_digits,
    redact_for_log,
    set_egress_overrides,
)
from app.modules.sniffer import get_sniffer_history

VISA = "4111111111111111"
SPLIT_PAN = "4111\n111111111111"
CLEAN = "The rear axle nominal PSI is 32 when tires are cold."


@pytest.fixture(autouse=True)
def _reset_egress_hooks():
    set_egress_overrides(and_fn=lambda _s, _p: True, inlp_fn=lambda _t: None)
    yield
    set_egress_overrides(and_fn=None, inlp_fn=None)


def test_newline_split_pan_fails_numbers_layer():
    verdict = audit_held_response(f"card {SPLIT_PAN}", pack_id="lab")
    assert verdict.passed is False
    assert verdict.layer == "numbers"
    assert VISA not in verdict.reason


def test_homoglyph_digits_fail_dlp_after_nfkc():
    fullwidth = "".join(chr(0xFF10 + int(ch)) for ch in VISA)
    assert VISA not in fullwidth
    assert reconstruct_digits(fullwidth) == VISA
    assert normalize_homoglyphs(fullwidth) == VISA
    verdict = audit_held_response(f"pan {fullwidth}", pack_id="lab")
    assert verdict.passed is False
    assert verdict.layer == "dlp"


def test_clean_on_corpus_passes_when_hooks_pass():
    verdict = audit_held_response(CLEAN, pack_id="lab-automotive")
    assert verdict.passed is True
    assert verdict.layer is None


def test_and_failure_is_not_alpha_rescued():
    set_egress_overrides(and_fn=lambda _s, _p: False, inlp_fn=lambda _t: None)
    verdict = audit_held_response(CLEAN, pack_id="lab")
    assert verdict.passed is False
    assert verdict.layer == "and"


def test_inlp_seam_can_cut():
    set_egress_overrides(and_fn=lambda _s, _p: True, inlp_fn=lambda _t: True)
    verdict = audit_held_response(CLEAN, pack_id="lab")
    assert verdict.passed is False
    assert verdict.layer == "inlp"


def test_redact_log_keeps_hash_and_last4_not_pan():
    blob = redact_for_log(f"leak {VISA}")
    assert VISA not in blob
    assert "1111" in blob
    assert "redacted:" in blob


@pytest.mark.asyncio
async def test_compliance_hold_does_not_deliver_split_pan(mock_llm_stream, monkeypatch):
    async def _fake_stream(*_a, **_k):
        yield 'data: {"choices": [{"delta": {"content": "4111\\n"}}]}\n\n'
        yield 'data: {"choices": [{"delta": {"content": "111111111111"}}]}\n\n'
        yield "data: [DONE]\n\n"

    from app.modules.providers.ollama import OllamaProvider

    monkeypatch.setattr(OllamaProvider, "stream_chat", _fake_stream)
    set_config(
        noise_enabled=False,
        cosine_enabled=False,
        excitation_enabled=False,
        egress_profile="compliance",
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Safe query"}) as response:
            body = ""
            async for chunk in response.aiter_text():
                body += chunk
                assert VISA not in body
    assert VISA not in body
    assert "[FW_BLOCK]" in body
    assert "[CONNECTION_TERMINATED]" in body
    traces = get_sniffer_history()
    if traces:
        assert VISA not in (traces[-1].response_content or "")


@pytest.mark.asyncio
async def test_compliance_hold_releases_clean_response(mock_llm_stream, monkeypatch):
    async def _fake_stream(*_a, **_k):
        yield f'data: {{"choices": [{{"delta": {{"content": "{CLEAN}"}}}}]}}\n\n'
        yield "data: [DONE]\n\n"

    from app.modules.providers.ollama import OllamaProvider

    monkeypatch.setattr(OllamaProvider, "stream_chat", _fake_stream)
    set_config(
        noise_enabled=False,
        cosine_enabled=False,
        excitation_enabled=False,
        egress_profile="compliance",
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Safe query"}) as response:
            body = ""
            async for chunk in response.aiter_text():
                body += chunk
    assert CLEAN in body
    assert "[FW_BLOCK]" not in body


@pytest.mark.asyncio
async def test_v1_proxy_hold_returns_403_on_pan(mock_llm_stream, monkeypatch):
    async def _fake_stream(*_a, **_k):
        yield f'data: {{"choices": [{{"delta": {{"content": "{VISA}"}}}}]}}\n\n'
        yield "data: [DONE]\n\n"

    from app.modules.providers.ollama import OllamaProvider

    monkeypatch.setattr(OllamaProvider, "stream_chat", _fake_stream)
    set_config(
        noise_enabled=False,
        cosine_enabled=False,
        excitation_enabled=False,
        egress_profile="compliance",
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post(
            "/v1/chat/completions",
            json={"model": "test", "messages": [{"role": "user", "content": "Safe query"}], "stream": False},
        )
    assert response.status_code == 403
    assert VISA not in response.text
    assert "security_breach" in response.text


def test_cut_message_does_not_echo_generation():
    assert VISA not in EGRESS_CUT_MESSAGE
    assert "4111" not in EGRESS_CUT_MESSAGE
