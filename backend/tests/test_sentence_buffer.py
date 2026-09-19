"""L08 — chat sentence buffer. Does not change compliance hold."""
from __future__ import annotations

from pathlib import Path

import httpx
import pytest

from app.core.firewall import SemanticFirewall
from app.core.state import set_config_sync as set_config
from app.main import app
from app.modules.egress import EGRESS_CUT_MESSAGE, set_egress_overrides
from app.modules.sentence_buffer import CHAT_DELIMITERS, SentenceBuffer, drain, gated_emit

VISA = "4111111111111111"
BUFFER_SOURCE = Path(__file__).resolve().parents[1] / "app" / "modules" / "sentence_buffer.py"


@pytest.fixture(autouse=True)
def _and_pass():
    set_egress_overrides(and_fn=lambda _s, _p: True, inlp_fn=lambda _t: None)
    yield
    set_egress_overrides(and_fn=None, inlp_fn=None)


def test_hola_mundo_is_two_evals_not_ingress_segment():
    parts = drain("hola. mundo")
    assert parts == ["hola.", " mundo"]
    assert drain("hola. mundo") != SemanticFirewall.segment("hola. mundo")
    source = BUFFER_SOURCE.read_text(encoding="utf-8")
    assert "from app.core.firewall" not in source
    assert "segment(" not in source
    assert CHAT_DELIMITERS == frozenset(".?;\n")


def test_push_does_not_emit_before_delimiter():
    buf = SentenceBuffer()
    assert buf.push("Hola") == []
    assert buf.pending == "Hola"
    assert buf.push(" mundo.") == ["Hola mundo."]
    assert buf.pending == ""


def test_semicolon_question_and_newline_are_delimiters():
    assert drain("a;b?c\nd") == ["a;", "b?", "c\n", "d"]


def test_breach_on_second_sentence_does_not_emit_it():
    emitted, passed = gated_emit(
        ["hola. ", "mundo."],
        eval_fn=lambda s: not s.strip().startswith("mundo"),
    )
    assert passed is False
    assert emitted == ["hola."]
    assert "mundo." not in "".join(emitted)


def test_tail_without_delimiter_is_evaluated_at_done():
    calls: list[str] = []

    def eval_fn(sentence: str) -> bool:
        calls.append(sentence)
        return True

    emitted, passed = gated_emit(["sin punto"], eval_fn)
    assert passed is True
    assert emitted == ["sin punto"]
    assert calls == ["sin punto"]


def test_newline_may_emit_pan_prefix_that_is_why_l07_exists():
    """Chat policy is the sentence. First half of a split PAN can leave.

    Compliance hold (L07) exists because this profile must not wait for the
    rest of the number. Do not 'fix' that here by mixing full-response hold.
    """
    buf = SentenceBuffer()
    first = buf.push("4111\n")
    assert first == ["4111\n"]
    tail = buf.flush_tail()
    assert tail == ""
    rest, _ok = gated_emit(["4111\n", "111111111111"], eval_fn=lambda _s: True)
    assert rest[0] == "4111\n"
    assert "4111\n" in "".join(rest)


def test_l12_semicolon_payload_is_its_own_sentence():
    parts = drain(f"Apriete de bujía 25 Nm; {VISA}")
    assert parts[0] == "Apriete de bujía 25 Nm;"
    assert VISA in parts[-1]


def test_l12_gated_emit_stops_before_dirty_clause():
    emitted, passed = gated_emit(
        ["Apriete de bujía 25 Nm; ", VISA],
        eval_fn=lambda s: VISA not in s,
    )
    assert passed is False
    assert VISA not in "".join(emitted)
    assert emitted == ["Apriete de bujía 25 Nm;"]


@pytest.mark.asyncio
async def test_chat_wrapper_bursts_on_delimiter_and_cuts_second(mock_llm_stream, monkeypatch):
    async def _fake_stream(*_a, **_k):
        yield 'data: {"choices": [{"delta": {"content": "hola. "}}]}\n\n'
        yield 'data: {"choices": [{"delta": {"content": "BREACH."}}]}\n\n'
        yield "data: [DONE]\n\n"

    from app.modules.providers.ollama import OllamaProvider

    monkeypatch.setattr(OllamaProvider, "stream_chat", _fake_stream)
    set_egress_overrides(and_fn=lambda s, _p: "BREACH" not in s, inlp_fn=lambda _t: None)
    set_config(
        noise_enabled=False,
        cosine_enabled=False,
        excitation_enabled=False,
        egress_profile="chat",
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Safe query"}) as response:
            body = ""
            async for chunk in response.aiter_text():
                body += chunk
    assert "hola." in body
    assert "BREACH." not in body
    assert "[FW_BLOCK]" in body
    assert EGRESS_CUT_MESSAGE.split("\n")[1] in body


@pytest.mark.asyncio
async def test_chat_wrapper_evaluates_tail_without_delimiter(mock_llm_stream, monkeypatch):
    async def _fake_stream(*_a, **_k):
        yield 'data: {"choices": [{"delta": {"content": "Mocked response"}}]}\n\n'
        yield "data: [DONE]\n\n"

    from app.modules.providers.ollama import OllamaProvider

    monkeypatch.setattr(OllamaProvider, "stream_chat", _fake_stream)
    set_config(
        noise_enabled=False,
        cosine_enabled=False,
        excitation_enabled=False,
        egress_profile="chat",
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Safe query"}) as response:
            body = ""
            async for chunk in response.aiter_text():
                body += chunk
    assert "Mocked response" in body
    assert "[FW_BLOCK]" not in body


@pytest.mark.asyncio
async def test_compliance_still_holds_split_pan(mock_llm_stream, monkeypatch):
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
