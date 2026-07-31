"""Unit tests for rompepepe state session manager.
"""
from pathlib import Path
import tempfile
import pytest
from rompepepe.state.models import TestResult, TelemetryTrace
from rompepepe.state.session_manager import SessionManager


def test_session_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        mgr = SessionManager(vault_path)

        # Create session
        session = mgr.create_session(strategy="grid_search", total_steps=10)
        assert session.strategy == "grid_search"
        assert session.status == "running"
        assert session.total_steps == 10

        # Append result & save
        res = TestResult(
            step=1,
            prompt="Test prompt",
            config={"cosine_threshold": 0.5315},
            passed=True,
            telemetry=TelemetryTrace(passed=True, text="Success"),
            duration_ms=12.5,
        )
        session.results.append(res)
        session.current_step = 1
        saved_path = mgr.save_session(session)
        assert saved_path.exists()

        # Load session
        loaded = mgr.load_session(session.session_id)
        assert loaded.session_id == session.session_id
        assert loaded.current_step == 1
        assert len(loaded.results) == 1
        assert loaded.results[0].prompt == "Test prompt"


def test_interrupted_session_recovery():
    with tempfile.TemporaryDirectory() as tmpdir:
        vault_path = Path(tmpdir)
        mgr = SessionManager(vault_path)

        session = mgr.create_session(strategy="adaptive_fuzzing", total_steps=20)
        session.status = "interrupted"
        mgr.save_session(session)

        interrupted = mgr.get_latest_interrupted_session()
        assert interrupted is not None
        assert interrupted.session_id == session.session_id
        assert interrupted.status == "interrupted"
