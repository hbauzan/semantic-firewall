"""Shared test fixtures and configuration.

Provides reusable TestClient, config reset helpers, and common imports
for all test modules (Finding Q5 — Test Suite Partitioning).
"""
import numpy as np
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.models import ConfigState
from app.core.state import set_config_sync as set_config


def mock_firewall_search_result() -> list[dict]:
    """Synthetic LanceDB hit so integration tests reach the vector pipeline."""
    vec = np.random.rand(1024).astype(np.float32)
    vec = (vec / np.linalg.norm(vec)).tolist()
    return [{
        "vector": vec,
        "sparse_lexical": {10: 1.0, 20: 0.5, 30: 0.25},
        "text": "Synthetic firewall context chunk for integration tests.",
        "metadata": '{"filename": "test.pdf"}',
    }]


@pytest.fixture
def firewall_context(monkeypatch):
    """Patch storage.search_for_firewall to return a synthetic corpus hit."""
    from app.modules.storage import storage

    def _fake_search(*_args, **_kwargs):
        return mock_firewall_search_result()

    monkeypatch.setattr(storage, "search_for_firewall", _fake_search)


# --- Shared TestClient (lifespan starts inference dispatcher) ---
_client_cm = TestClient(app)
client = _client_cm.__enter__()


def pytest_sessionfinish(session, exitstatus):
    _client_cm.__exit__(None, None, None)


@pytest.fixture
def mock_llm_stream(monkeypatch):
    """Stub the default (Ollama) provider's stream_chat with a deterministic
    fake, so PASS-path tests never reach a live model.

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
        raw_entropy_limit=3.0,
        cosine_order=1,
        excitation_order=3,
        noise_order=2,
        adaptive_factor=0.85,
        rag_top_k=3,
        noise_enabled=True,
        cosine_enabled=True,
        excitation_enabled=True,
        firewall_mode="positive",
        active_tab="chat",
        active_corpus_file=None,
        calibration_coverage="recommended",
    )
