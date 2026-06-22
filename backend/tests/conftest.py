"""Shared test fixtures and configuration.

Provides reusable TestClient, config reset helpers, and common imports
for all test modules (Finding Q5 — Test Suite Partitioning).
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.models import ConfigState
from app.core.state import set_config_sync as set_config


# --- Shared TestClient ---
client = TestClient(app)


@pytest.fixture
def mock_llm_stream(monkeypatch):
    """Stub the default (Ollama) provider's stream_chat with a deterministic
    fake, so PASS-path tests never reach a live model (dev-protocol §3.2).

    Mirrors the inline mock already used in test_openai_proxy_v1_compliance,
    centralized here for reuse. Yields OpenAI-style SSE chunks, which both
    /chat (_stream_via_provider) and /v1/chat/completions parse identically.
    """
    from app.modules.providers.ollama import OllamaProvider

    async def _fake_stream(*args, **kwargs):
        yield 'data: {"choices": [{"delta": {"content": "Mocked response"}}]}\n\n'
        yield "data: [DONE]\n\n"

    monkeypatch.setattr(OllamaProvider, "stream_chat", _fake_stream)
    return _fake_stream


@pytest.fixture(autouse=True)
def reset_config_after_test():
    """Ensure config state is reset to defaults after each test to prevent bleed."""
    yield
    set_config(
        excitation_threshold=150,
        noise_tolerance=0.005,
        cosine_threshold=0.5315,
        global_noise_limit=4.5,
        cosine_order=2,
        excitation_order=3,
        noise_order=1,
        adaptive_factor=0.85,
        rag_top_k=3,
        noise_enabled=True,
        cosine_enabled=True,
        excitation_enabled=True,
        firewall_mode="positive",
        active_tab="chat",
    )
