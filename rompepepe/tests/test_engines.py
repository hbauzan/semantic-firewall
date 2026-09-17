"""Unit tests for rompepepe engines and report generator.
"""
from pathlib import Path
import tempfile
from unittest.mock import AsyncMock, MagicMock
import pytest

from rompepepe.engines.grid_search import generate_config_grid, GridSearchEngine
from rompepepe.engines.adaptive_fuzzing import AdaptiveFuzzingEngine
from rompepepe.reports.generator import ReportGenerator
from rompepepe.state.models import SessionState, TestResult, TelemetryTrace, BoundaryTrace


def test_generate_config_grid():
    grid = generate_config_grid(
        cosine_thresholds=[0.5],
        excitation_thresholds=[150],
        noise_limits=[4.5],
        modes=["positive"],
        filter_toggles=[(True, True, True)],
        orders=[(1, 2, 3)],
    )
    assert len(grid) == 1
    assert grid[0]["cosine_threshold"] == 0.5
    assert grid[0]["firewall_mode"] == "positive"


def test_generate_config_grid_tiers():
    light_grid = generate_config_grid(tier="light")
    normal_grid = generate_config_grid(tier="normal")
    heavy_grid = generate_config_grid(tier="heavy")

    assert len(light_grid) < len(normal_grid) < len(heavy_grid)
    assert len(light_grid) == 2
    assert len(heavy_grid) > 100


@pytest.mark.asyncio
async def test_grid_search_engine_preflight():
    fw_client = MagicMock()
    fw_client.audit = AsyncMock(return_value=TelemetryTrace(passed=True))
    session_mgr = MagicMock()

    engine = GridSearchEngine(fw_client, session_mgr)
    grid = [{"cosine_threshold": 0.5315}]
    preflight = await engine.estimate_preflight(grid, dataset_size=5)

    assert preflight["total_grid_cells"] == 1
    assert preflight["total_tests"] == 5
    assert "formatted_eta" in preflight


def test_report_generator():
    with tempfile.TemporaryDirectory() as tmpdir:
        reports_dir = Path(tmpdir)
        gen = ReportGenerator(reports_dir)

        session = SessionState(
            session_id="test_session_123",
            strategy="adaptive_fuzzing",
            status="completed",
            created_at="2026-07-31T00:00:00",
            updated_at="2026-07-31T00:05:00",
            total_steps=2,
            current_step=2,
            results=[
                TestResult(
                    step=1,
                    prompt="Query 1",
                    config={"cosine_threshold": 0.5315},
                    passed=True,
                    telemetry=TelemetryTrace(passed=True, text="Ok"),
                    duration_ms=15.0,
                ),
                TestResult(
                    step=2,
                    prompt="Query 2",
                    config={"cosine_threshold": 0.5315},
                    passed=False,
                    breach_reason="cosine_threshold",
                    telemetry=TelemetryTrace(passed=False, breach_reason="cosine_threshold", text="Blocked"),
                    duration_ms=18.0,
                ),
            ],
            boundary_traces=[
                BoundaryTrace(
                    step_a=1,
                    step_b=2,
                    prompt_a="Query 1",
                    prompt_b="Query 2",
                    passed_a=True,
                    passed_b=False,
                    cosine_a=0.51,
                    cosine_b=0.55,
                    mutation_description="State flip",
                    timestamp="2026-07-31T00:02:00",
                )
            ]
        )

        report_file = gen.generate_report(session)
        assert report_file.exists()
        content = report_file.read_text(encoding="utf-8")
        assert "Quality Assurance & Semantic Boundary Report" in content
        assert "test_session_123" in content
        assert "Boundary Transition #1" in content
