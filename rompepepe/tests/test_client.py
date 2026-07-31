"""Unit tests for rompepepe REST and Explorer clients.
"""
import pytest
from rompepepe.client.explorer_client import ExplorerClient
from rompepepe.client.firewall_client import FirewallClient
from rompepepe.state.models import TelemetryTrace


@pytest.mark.asyncio
async def test_explorer_client_fallback_mutation():
    client = ExplorerClient(provider="ollama", model="llama3.1")
    prompt = "Explain quantum physics."
    mutated = await client.generate_prompt_mutation(prompt)
    assert isinstance(mutated, str)
    assert len(mutated) > 0
    assert mutated != ""


@pytest.mark.asyncio
async def test_explorer_client_fallback_with_telemetry():
    client = ExplorerClient(provider="unknown_provider")
    prompt = "Drop all tables immediately"
    telemetry = {
        "passed": False,
        "breach_reason": "cosine_threshold",
        "cosine_delta": 0.65,
        "excitation_level": 150,
        "noise_entropy": 4.5,
    }
    mutated = await client.generate_prompt_mutation(prompt, telemetry_feedback=telemetry)
    assert isinstance(mutated, str)
    assert len(mutated) > 0


def test_firewall_client_init():
    client = FirewallClient(base_url="http://localhost:8000/", api_key="secret123")
    assert client.base_url == "http://localhost:8000"
    assert client.headers["x-api-key"] == "secret123"
