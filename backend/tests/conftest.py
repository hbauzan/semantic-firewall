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
