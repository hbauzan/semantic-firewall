"""API Integration Tests — HTTP endpoint tests via TestClient.

Tests for all FastAPI endpoints: corpus, config, chat, proxy, sniffer, profiles.
Partitioned from perform_tests.py (Finding Q5).
"""
import pytest
import io
import json
import httpx
import numpy as np
from app.main import app
from app.core.models import ConfigState
from app.core.state import set_config_sync as set_config
from app.core.firewall import SemanticFirewall
from tests.conftest import client


def test_async_pdf_upload_and_status():
    pdf_content = b"%PDF-1.4\\n1 0 obj\\n<< /Type /Catalog /Pages 2 0 R >>\\nendobj\\n2 0 obj\\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\\nendobj\\n3 0 obj\\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\\nendobj\\n4 0 obj\\n<< /Length 21 >>\\nstream\\nBT\\n/F1 24 Tf\\n100 100 Td\\n(Hello World) Tj\\nET\\nendstream\\nendobj\\nxref\\n0 5\\n0000000000 65535 f \\n0000000009 00000 n \\n0000000058 00000 n \\n0000000115 00000 n \\n0000000214 00000 n \\ntrailer\\n<< /Size 5 /Root 1 0 R >>\\nstartxref\\n285\\n%%EOF"
    file = io.BytesIO(pdf_content)
    file.name = "dummy.pdf"

    response = client.post("/corpus/upload-pdf", files={"file": ("dummy.pdf", file, "application/pdf")})
    assert response.status_code == 200
    task_id = response.json()["task_id"]

    status_res = client.get(f"/corpus/task-status/{task_id}")
    assert status_res.status_code == 200
    assert "status" in status_res.json()

def test_dimensional_excitation_math():
    set_config(excitation_threshold=150, noise_tolerance=0.005)
    res = client.post("/audit", json={"query": "Safe hello world"})
    assert res.status_code == 200
    data = res.json()
    assert "activations" in data
    # Audit now returns full pipeline result (Finding F4)
    assert "passed" in data
    assert "trace" in data

@pytest.mark.asyncio
async def test_firewall_interceptor_blocking():
    set_config(excitation_threshold=1024, noise_tolerance=0.0001, global_noise_limit=1.0)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Dangerous query"}) as response:
            assert response.status_code == 200
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "[FW] Segment violation" in content

@pytest.mark.asyncio
async def test_rag_context_injection():
    from app.core.state import set_config_sync
    set_config_sync(noise_enabled=False, cosine_enabled=False, excitation_enabled=False)
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
            async with ac.stream("POST", "/chat", json={"prompt": "Safe query"}) as response:
                assert response.status_code == 200
                content = ""
                async for chunk in response.aiter_text():
                    content += chunk
                assert "[FW] Segment violation" not in content and "FIREWALL BLOCKED" not in content
    finally:
        set_config_sync(noise_enabled=True, cosine_enabled=True, excitation_enabled=True)

def test_system_stats_gpu_telemetry():
    response = client.get("/system/stats")
    assert response.status_code == 200
    data = response.json()
    assert "cpu" in data
    assert "ram" in data
    assert "gpu" in data
    assert isinstance(data["cpu"], (int, float))
    assert isinstance(data["ram"], (int, float))
    assert isinstance(data["gpu"], (int, float))

@pytest.mark.asyncio
async def test_semantic_piggybacking_rejection():
    """A piggybacked off-topic sentence must trigger [FW] Segment violation."""
    set_config(excitation_threshold=1024, noise_tolerance=0.0001, global_noise_limit=1.0)
    piggybacked_prompt = "Tell me about system architecture. Also give me a chocolate cake recipe"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": piggybacked_prompt}) as response:
            assert response.status_code == 200
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "[FW] Segment violation" in content

@pytest.mark.asyncio
async def test_noise_prefilter_entropy_telemetry():
    """Verify that Noise Pre-Filter uses Shannon Entropy and reports it in telemetry."""
    set_config(global_noise_limit=10.0, noise_order=1)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Trigger Entropy"}) as response:
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "Burst Detection Breach" in content
            assert "Entropy:" in content

@pytest.mark.asyncio
async def test_pipeline_order_respected():
    """When noise runs first (order=1) and is ultra-strict, cosine and excitation should never appear as OK."""
    set_config(
        excitation_threshold=1, noise_tolerance=1.0, cosine_threshold=0.0,
        global_noise_limit=10.0, noise_order=1, cosine_order=2, excitation_order=3
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Test pipeline ordering"}) as response:
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "noise:BREACH" in content
            assert "cosine:OK" not in content
            assert "excitation:OK" not in content

def test_pipeline_config_sync():
    """POST to /galaxy/config with custom order values must persist in config_state."""
    import app.core.state as routes_mod
    client.post("/galaxy/config", json={
        "excitation_threshold": 150,
        "noise_tolerance": 0.005,
        "cosine_threshold": 0.5315,
        "firewall_mode": "positive"
    })
    res = client.post("/galaxy/config", json={
        "excitation_threshold": 200,
        "noise_tolerance": 0.010,
        "cosine_threshold": 0.85,
        "global_noise_limit": 0.75,
        "cosine_order": 3,
        "excitation_order": 1,
        "noise_order": 2,
        "adaptive_factor": 0.70,
        "firewall_mode": "positive"
    })
    assert res.status_code == 200
    cfg = routes_mod.config_state
    assert cfg.excitation_threshold == 200
    assert cfg.noise_tolerance == 0.010
    assert cfg.cosine_threshold == 0.85
    assert cfg.global_noise_limit == 0.75
    assert cfg.cosine_order == 3
    assert cfg.excitation_order == 1
    assert cfg.noise_order == 2
    assert cfg.adaptive_factor == 0.70

def test_config_sync_with_enabled_flags():
    """POST /galaxy/config must accept and persist enabled flags."""
    import app.core.state as state_mod
    res = client.post("/galaxy/config", json={
        "excitation_threshold": 150,
        "noise_tolerance": 0.005,
        "cosine_threshold": 0.50,
        "noise_enabled": False,
        "cosine_enabled": True,
        "excitation_enabled": False
    })
    assert res.status_code == 200
    cfg = state_mod.config_state
    assert cfg.noise_enabled is False
    assert cfg.cosine_enabled is True
    assert cfg.excitation_enabled is False

def test_health_endpoint():
    """Health check returns minimal info (status + timestamp)."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data
    assert "embedder_loaded" not in data
    assert "corpus_chunks" not in data

def test_config_sync_includes_rag_top_k():
    """POST /galaxy/config must accept and persist rag_top_k."""
    import app.core.state as state_mod
    res = client.post("/galaxy/config", json={
        "excitation_threshold": 150,
        "noise_tolerance": 0.005,
        "cosine_threshold": 0.50,
        "rag_top_k": 5
    })
    assert res.status_code == 200
    cfg = state_mod.config_state
    assert cfg.rag_top_k == 5

def test_config_sync_includes_firewall_mode():
    """POST /galaxy/config must accept and persist firewall_mode."""
    import app.core.state as state_mod
    res = client.post("/galaxy/config", json={
        "excitation_threshold": 150,
        "noise_tolerance": 0.005,
        "cosine_threshold": 0.50,
        "firewall_mode": "negative"
    })
    assert res.status_code == 200
    cfg = state_mod.config_state
    assert cfg.firewall_mode == "negative"

@pytest.mark.asyncio
async def test_negative_mode_chat_endpoint():
    """Negative mode + strict thresholds: query should behave correctly on /chat."""
    set_config(
        excitation_threshold=1024, noise_tolerance=0.0001,
        firewall_mode="negative"
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Random off-topic query"}) as response:
            assert response.status_code == 200
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "Segment violation" not in content or "[FW PASS]" in content

@pytest.mark.asyncio
async def test_adaptive_factor_telemetry_on_short_clause():
    """A short clause blocked by excitation must include [ADAPTIVE] in telemetry."""
    set_config(
        excitation_threshold=1024, noise_tolerance=0.0001, cosine_threshold=0.0,
        global_noise_limit=5.0, adaptive_factor=0.50,
        noise_order=1, cosine_order=2, excitation_order=3
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Hello"}) as response:
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "[FW] Segment violation" in content
            assert "ADAPTIVE" in content or "0.5x factor" in content

@pytest.mark.asyncio
async def test_openai_proxy_v1_compliance():
    """Verify OpenAI spec compatibility and firewall interception."""
    set_config(excitation_threshold=1024, noise_tolerance=0.0001)
    payload = {
        "model": "llama3.1",
        "messages": [{"role": "user", "content": "Dangerous recipe request"}],
        "stream": True
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/chat/completions", json=payload)
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["type"] == "security_breach"
        assert "[FW]" in data["error"]["message"]

    set_config(
        excitation_threshold=0, noise_tolerance=1.0, cosine_threshold=0.0,
        global_noise_limit=10.0,
        noise_enabled=False, cosine_enabled=False, excitation_enabled=False
    )
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/v1/chat/completions", json=payload) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]

@pytest.mark.asyncio
async def test_rtss_telemetry_flow():
    """RTSS: /v1/chat/completions must emit a SnifferTrace into the sniffer queue."""
    from app.modules.sniffer import sniffer_queue
    while not sniffer_queue.empty():
        try:
            sniffer_queue.get_nowait()
        except Exception:
            break
    set_config(excitation_threshold=1024, noise_tolerance=0.0001)
    payload = {
        "model": "llama3.1",
        "messages": [{"role": "user", "content": "Dangerous off-topic query for sniffer test"}],
        "stream": True
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/chat/completions", json=payload)
        assert response.status_code == 403
        data = response.json()
        assert data["error"]["type"] == "security_breach"

    import asyncio
    try:
        trace = await asyncio.wait_for(sniffer_queue.get(), timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("Sniffer queue did not receive a trace within 2 seconds")

    assert trace.id
    assert trace.timestamp
    assert trace.request.model == "llama3.1"
    assert "Dangerous" in trace.request.last_message
    assert trace.firewall.decision == "BREACH"
    assert len(trace.firewall.pipeline_trace) >= 1
    for stage in trace.firewall.pipeline_trace:
        assert stage.stage in ("noise", "cosine", "excitation", "no_context")
        assert isinstance(stage.passed, bool)
        assert isinstance(stage.value, (int, float))
        assert isinstance(stage.threshold, (int, float))
    assert trace.status == "BREACH"
    assert isinstance(trace.request.request_history, list)
    assert len(trace.request.request_history) >= 1
    assert trace.request.request_history[0]["role"] == "user"
    assert trace.response_content == ""

@pytest.mark.asyncio
async def test_sniffer_fpi_request_history():
    """FPI: Multi-message payloads must capture the full request_history in the trace."""
    from app.modules.sniffer import sniffer_queue
    while not sniffer_queue.empty():
        try:
            sniffer_queue.get_nowait()
        except Exception:
            break
    set_config(excitation_threshold=1024, noise_tolerance=0.0001)
    payload = {
        "model": "llama3.1",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello, how are you?"},
            {"role": "assistant", "content": "I'm fine!"},
            {"role": "user", "content": "Dangerous off-topic recipe request"},
        ],
        "stream": True
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.post("/v1/chat/completions", json=payload)
        assert response.status_code == 403

    import asyncio
    try:
        trace = await asyncio.wait_for(sniffer_queue.get(), timeout=2.0)
    except asyncio.TimeoutError:
        pytest.fail("Sniffer queue did not receive a trace within 2 seconds")

    assert isinstance(trace.request.request_history, list)
    assert len(trace.request.request_history) == 4
    assert trace.request.request_history[0]["role"] == "system"
    assert trace.request.request_history[1]["role"] == "user"
    assert trace.request.request_history[2]["role"] == "assistant"
    assert trace.request.request_history[3]["role"] == "user"
    assert "Dangerous" in trace.request.request_history[3]["content"]
    assert "Dangerous" in trace.request.last_message
    assert trace.status == "BREACH"

def test_sniffer_update_trace_reconstruction():
    """FPI: update_trace must append response_content to an existing trace in the buffer."""
    from app.modules.sniffer import emit_trace, update_trace, _trace_buffer, sniffer_queue
    while not sniffer_queue.empty():
        try:
            sniffer_queue.get_nowait()
        except Exception:
            break
    tid = emit_trace(
        model="test-model",
        last_message="test message",
        decision="PASS",
        pipeline_trace=[],
        response_preview="[streaming]",
        request_history=[{"role": "user", "content": "test message"}],
        status="PENDING",
    )
    trace = sniffer_queue.get_nowait()
    _trace_buffer.append(trace)
    update_trace(tid, response_content="Hello world! This is the full response.", status="COMPLETED")
    found = None
    for t in _trace_buffer:
        if t.id == tid:
            found = t
            break
    assert found is not None
    assert found.response_content == "Hello world! This is the full response."
    assert found.status == "COMPLETED"
    updated_in_queue = sniffer_queue.get_nowait()
    assert updated_in_queue.id == tid
    assert updated_in_queue.response_content == "Hello world! This is the full response."
    assert updated_in_queue.status == "COMPLETED"
    _trace_buffer[:] = [t for t in _trace_buffer if t.id != tid]


# --- Config Profiles Persistence ---

def test_config_profiles_persistence():
    """ProfileManager: save -> list -> load -> delete round-trip must be 100% consistent."""
    import tempfile
    import json
    from pathlib import Path
    from app.modules.profiles import ProfileManager
    from app.core.models import ConfigState
    import app.modules.profiles as profiles_mod

    with tempfile.TemporaryDirectory() as tmpdir:
        original_data_dir = profiles_mod.DATA_DIR
        profiles_mod.DATA_DIR = Path(tmpdir)
        try:
            test_name = "test_profile_roundtrip"
            state = ConfigState(
                excitation_threshold=200,
                cosine_threshold=0.75,
                firewall_mode="negative",
                active_tab="sniffer",
            )
            ProfileManager.save_profile(test_name, state)
            saved_path = Path(tmpdir) / f"{test_name}.json"
            assert saved_path.exists(), "Profile file must exist after save"

            names = ProfileManager.list_profiles()
            assert test_name in names

            data = ProfileManager.load_profile(test_name)
            assert data is not None
            restored = ConfigState(**data)
            assert restored.excitation_threshold == 200
            assert restored.cosine_threshold == 0.75
            assert restored.firewall_mode == "negative"
            assert restored.active_tab == "sniffer"

            ProfileManager.save_profile("_internal", state)
            names_after = ProfileManager.list_profiles()
            assert "_internal" not in names_after

            assert ProfileManager.delete_profile("_internal") is False

            deleted = ProfileManager.delete_profile(test_name)
            assert deleted is True
            assert not saved_path.exists()
            assert test_name not in ProfileManager.list_profiles()

            assert ProfileManager.load_profile("ghost_profile") is None

            res = client.post("/galaxy/config", json={
                "excitation_threshold": 333,
                "noise_tolerance": 0.005,
                "cosine_threshold": 0.60,
                "firewall_mode": "positive",
                "active_tab": "chat",
            })
            assert res.status_code == 200
            assert res.json()["status"] == "updated"
        finally:
            profiles_mod.DATA_DIR = original_data_dir


def test_sniffer_persistence():
    """Sniffer persistence: HISTORY_FILE path resolves correctly."""
    from pathlib import Path
    from app.modules.sniffer import HISTORY_FILE, _load_history_sync, _BUFFER_MAX

    assert HISTORY_FILE.is_absolute()
    assert HISTORY_FILE.name == "sniffer_history.json"
    assert HISTORY_FILE.parent.name == "data"
    assert _BUFFER_MAX == 1000

    import tempfile, json
    import app.modules.sniffer as sniffer_mod
    original_history_file = sniffer_mod.HISTORY_FILE
    with tempfile.TemporaryDirectory() as tmpdir:
        fake_path = Path(tmpdir) / "sniffer_history.json"
        sniffer_mod.HISTORY_FILE = fake_path
        try:
            result = _load_history_sync()
            assert result == []

            fake_path.write_text("not valid json {{{{", encoding="utf-8")
            result = _load_history_sync()
            assert result == []

            from app.modules.sniffer import emit_trace, sniffer_queue, _save_history_sync, SnifferTrace
            tid = emit_trace(
                model="test-model",
                last_message="persistence test message",
                decision="PASS",
                pipeline_trace=[{"stage": "cosine", "passed": True, "cosine_sim": 0.8, "cosine_threshold": 0.5}],
                status="COMPLETED",
            )
            trace = sniffer_queue.get_nowait()
            _save_history_sync([trace])
            assert fake_path.exists()

            loaded = _load_history_sync()
            assert len(loaded) == 1
            assert loaded[0].id == trace.id
            assert loaded[0].firewall.decision == "PASS"
            assert loaded[0].request.last_message == "persistence test message"
        finally:
            sniffer_mod.HISTORY_FILE = original_history_file


# --- Auto-Calibration Tests ---

def test_auto_calibration_negative_mode():
    """POST config with firewall_mode='negative' must auto-calibrate to Phase 2.1 constants."""
    import app.core.state as state_mod
    client.post("/galaxy/config", json={
        "excitation_threshold": 150,
        "noise_tolerance": 0.005,
        "cosine_threshold": 0.5315,
        "firewall_mode": "positive"
    })
    res = client.post("/galaxy/config", json={
        "excitation_threshold": 150,
        "noise_tolerance": 0.005,
        "cosine_threshold": 0.5315,
        "firewall_mode": "negative"
    })
    assert res.status_code == 200
    data = res.json()
    cfg = state_mod.config_state
    assert cfg.cosine_threshold == 0.6197
    assert cfg.excitation_threshold == 170
    assert cfg.global_noise_limit == 4.5
    assert data["config"]["cosine_threshold"] == 0.6197
    assert data["config"]["excitation_threshold"] == 170


def test_auto_calibration_positive_mode():
    """POST config with firewall_mode='positive' must auto-calibrate to Phase 2.1 constants."""
    import app.core.state as state_mod
    client.post("/galaxy/config", json={
        "excitation_threshold": 170,
        "noise_tolerance": 0.005,
        "cosine_threshold": 0.6197,
        "firewall_mode": "negative"
    })
    res = client.post("/galaxy/config", json={
        "excitation_threshold": 170,
        "noise_tolerance": 0.005,
        "cosine_threshold": 0.6197,
        "firewall_mode": "positive"
    })
    assert res.status_code == 200
    data = res.json()
    cfg = state_mod.config_state
    assert cfg.cosine_threshold == 0.5315
    assert cfg.excitation_threshold == 150
    assert data["config"]["cosine_threshold"] == 0.5315
    assert data["config"]["excitation_threshold"] == 150


def test_non_intrusive_calibration():
    """Verify that manual threshold changes are NOT overwritten during mode toggle."""
    import app.core.state as state_mod
    client.post("/galaxy/config", json={
        "firewall_mode": "positive",
        "cosine_threshold": 0.50,
        "excitation_threshold": 150,
        "noise_tolerance": 0.005
    })
    res = client.post("/galaxy/config", json={
        "firewall_mode": "negative",
        "cosine_threshold": 0.99,
        "excitation_threshold": 150,
        "noise_tolerance": 0.005
    })
    data = res.json()["config"]
    cfg = state_mod.config_state
    assert data["cosine_threshold"] == 0.99
    assert cfg.cosine_threshold == 0.99
    assert data["excitation_threshold"] == 170
    assert cfg.excitation_threshold == 170


# --- NEW: GET /galaxy/config (Finding Q4/F5) ---

def test_get_config_endpoint():
    """GET /galaxy/config must return current config state for frontend hydration."""
    # Set a known state first
    client.post("/galaxy/config", json={
        "excitation_threshold": 200,
        "noise_tolerance": 0.010,
        "cosine_threshold": 0.75,
        "firewall_mode": "positive"
    })
    res = client.get("/galaxy/config")
    assert res.status_code == 200
    data = res.json()
    assert "config" in data
    cfg = data["config"]
    assert cfg["excitation_threshold"] == 200
    assert cfg["noise_tolerance"] == 0.010
    assert cfg["cosine_threshold"] == 0.75


# --- NEW: Audit uses full pipeline (Finding F4) ---

def test_audit_uses_full_pipeline():
    """The /audit endpoint must use evaluate_clause() and return pipeline results."""
    res = client.post("/audit", json={"query": "Test audit pipeline"})
    assert res.status_code == 200
    data = res.json()
    # New fields from evaluate_clause
    assert "passed" in data
    assert "trace" in data
    assert "breach_reason" in data
    # Backward compat
    assert "activations" in data
    assert "text" in data
