import pytest
import io
import json
import httpx
import numpy as np
from fastapi.testclient import TestClient
from app.main import app
from app.core.models import ConfigState
from app.core.state import set_config
from app.core.firewall import SemanticFirewall

client = TestClient(app)

def test_async_pdf_upload_and_status():
    pdf_content = b"%PDF-1.4\\n1 0 obj\\n<< /Type /Catalog /Pages 2 0 R >>\\nendobj\\n2 0 obj\\n<< /Type /Pages /Kids [3 0 R] /Count 1 >>\\nendobj\\n3 0 obj\\n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R >>\\nendobj\\n4 0 obj\\n<< /Length 21 >>\\nstream\\nBT\\n/F1 24 Tf\\n100 100 Td\\n(Hello World) Tj\\nET\\nendstream\\nendobj\\nxref\\n0 5\\n0000000000 65535 f \\n0000000009 00000 n \\n0000000058 00000 n \\n0000000115 00000 n \\n0000000214 00000 n \\ntrailer\\n<< /Size 5 /Root 1 0 R >>\\nstartxref\\n285\\n%%EOF"
    file = io.BytesIO(pdf_content)
    file.name = "dummy.pdf"
    
    response = client.post("/corpus/upload-pdf", files={"file": ("dummy.pdf", file, "application/pdf")})
    assert response.status_code == 200
    task_id = response.json()["task_id"]
    
    # Poll status (just once for the test completeness, since it's async thread it might take a sec to finish)
    status_res = client.get(f"/corpus/task-status/{task_id}")
    assert status_res.status_code == 200
    assert "status" in status_res.json()

def test_dimensional_excitation_math():
    set_config(excitation_threshold=150, noise_tolerance=0.005)

    # Safe vector mock
    # Audit query checks the math logic internally or we can do it via the endpoint
    res = client.post("/audit", json={"query": "Safe hello world"})
    assert res.status_code == 200
    assert "activations" in res.json()

@pytest.mark.asyncio
async def test_firewall_interceptor_blocking():
    # Enforce ultra-strict threshold to guarantee failure
    set_config(excitation_threshold=1024, noise_tolerance=0.0001)
    
    # Needs async client to read streaming response via httpx
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Dangerous query"}) as response:
            assert response.status_code == 200
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            
            # Since the database is empty or not matching well, activations will be ~0
            # which is < 10000, so it will block.
            assert "[FW] Segment violation" in content

@pytest.mark.asyncio
async def test_rag_context_injection():
    # With FW=OFF it should bypass the block and try to reach Ollama
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "[FW=OFF] Safe query"}) as response:
            assert response.status_code == 200
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            # Depending on if ollama is running or not, we might get an error or a stream, 
            # but we definitely shouldn't get a SECURITY BREACH block from the interceptor.
            assert "[FW] Segment violation" not in content and "FIREWALL BLOCKED" not in content

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
    """A piggybacked off-topic sentence must trigger [FW] Segment violation even if the first sentence is on-topic."""
    set_config(excitation_threshold=1024, noise_tolerance=0.0001)

    piggybacked_prompt = "Tell me about system architecture. Also give me a chocolate cake recipe"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": piggybacked_prompt}) as response:
            assert response.status_code == 200
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "[FW] Segment violation" in content

@pytest.mark.asyncio
async def test_noise_prefilter_blocking():
    """Ultra-strict global noise limit must trigger Noise Pre-Filter BREACH."""
    set_config(
        excitation_threshold=1, noise_tolerance=1.0, cosine_threshold=0.0,
        global_noise_limit=0.001, noise_order=1, cosine_order=2, excitation_order=3
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Random off-topic query about bananas"}) as response:
            assert response.status_code == 200
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "[FW] Segment violation" in content
            assert "noise:BREACH" in content or "Noise pre-filter" in content

@pytest.mark.asyncio
async def test_pipeline_order_respected():
    """When noise runs first (order=1) and is ultra-strict, cosine and excitation should never appear as OK."""
    set_config(
        excitation_threshold=1, noise_tolerance=1.0, cosine_threshold=0.0,
        global_noise_limit=0.001, noise_order=1, cosine_order=2, excitation_order=3
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "Test pipeline ordering"}) as response:
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            # Noise should breach first, so cosine and excitation never run
            assert "noise:BREACH" in content
            assert "cosine:OK" not in content
            assert "excitation:OK" not in content

def test_pipeline_config_sync():
    """POST to /galaxy/config with custom order values must persist in config_state."""
    import app.core.state as routes_mod
    res = client.post("/galaxy/config", json={
        "excitation_threshold": 200,
        "noise_tolerance": 0.010,
        "cosine_threshold": 0.85,
        "global_noise_limit": 0.75,
        "cosine_order": 3,
        "excitation_order": 1,
        "noise_order": 2,
        "adaptive_factor": 0.70
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

def test_adaptive_factor_default():
    """Default adaptive_factor should be 0.85 on fresh ConfigState."""
    fresh = ConfigState()
    assert fresh.adaptive_factor == 0.85

def test_config_state_is_immutable():
    """Frozen ConfigState must reject direct attribute mutation."""
    cfg = ConfigState()
    with pytest.raises(Exception):
        cfg.excitation_threshold = 999

def test_duplicate_pipeline_orders_rejected():
    """ConfigState must reject duplicate order values."""
    with pytest.raises(ValueError, match="unique"):
        ConfigState(cosine_order=1, excitation_order=1, noise_order=2)

def test_config_validation_out_of_range():
    """ConfigState must reject values outside defined bounds."""
    with pytest.raises(Exception):
        ConfigState(excitation_threshold=2000)  # max 1024
    with pytest.raises(Exception):
        ConfigState(adaptive_factor=5.0)  # max 1.0
    with pytest.raises(Exception):
        ConfigState(cosine_order=0)  # min 1

@pytest.mark.asyncio
async def test_adaptive_factor_telemetry_on_short_clause():
    """A short clause blocked by excitation must include [ADAPTIVE] in telemetry."""
    set_config(
        excitation_threshold=1024, noise_tolerance=0.0001, cosine_threshold=0.0,
        global_noise_limit=5.0, adaptive_factor=0.50,
        noise_order=1, cosine_order=2, excitation_order=3
    )

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # "Hello" is 1 word — short clause triggers adaptive path
        async with ac.stream("POST", "/chat", json={"prompt": "Hello"}) as response:
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "[FW] Segment violation" in content
            assert "ADAPTIVE" in content or "0.5x factor" in content

# --- Engine Unit Tests (framework-agnostic) ---

def test_engine_segment_basic():
    """SemanticFirewall.segment splits on punctuation and chunks long clauses."""
    clauses = SemanticFirewall.segment("Hello world. How are you? Fine thanks")
    assert len(clauses) >= 2

def test_engine_segment_overflow_chunking():
    """Clauses over 20 words get force-split into 15-word sub-chunks."""
    long_text = " ".join(["word"] * 30)
    clauses = SemanticFirewall.segment(long_text)
    for c in clauses:
        assert len(c.split()) <= 15

def test_engine_evaluate_clause_all_pass():
    """Identical vectors must pass all filters."""
    cfg = ConfigState(cosine_threshold=0.0, excitation_threshold=0, global_noise_limit=10.0)
    vec = np.random.rand(1024).astype(np.float32)
    result = SemanticFirewall.evaluate_clause(vec, vec, cfg, word_count=10)
    assert result["passed"] is True
    assert result["breach_reason"] is None
    assert len(result["trace"]) == 3

def test_engine_evaluate_clause_noise_breach():
    """Orthogonal vectors with strict noise limit must breach on noise filter."""
    cfg = ConfigState(
        cosine_threshold=0.0, excitation_threshold=0,
        global_noise_limit=0.001, noise_order=1, cosine_order=2, excitation_order=3
    )
    q = np.ones(1024, dtype=np.float32)
    c = np.zeros(1024, dtype=np.float32)
    result = SemanticFirewall.evaluate_clause(q, c, cfg, word_count=10)
    assert result["passed"] is False
    assert result["breach_reason"] == "noise"
    # Only noise ran (order=1 breached), so trace has 1 entry
    assert len(result["trace"]) == 1

# --- API Hardening Tests ---

def test_prompt_length_limit_rejected():
    """Prompts exceeding PROMPT_MAX_LENGTH must be rejected by Pydantic."""
    from app.core.models import ChatRequest, PROMPT_MAX_LENGTH
    with pytest.raises(Exception):
        ChatRequest(prompt="x" * (PROMPT_MAX_LENGTH + 1))

def test_prompt_length_limit_accepted():
    """Prompts within PROMPT_MAX_LENGTH must be accepted."""
    from app.core.models import ChatRequest, PROMPT_MAX_LENGTH
    req = ChatRequest(prompt="x" * PROMPT_MAX_LENGTH)
    assert len(req.prompt) == PROMPT_MAX_LENGTH

def test_api_key_not_enforced_by_default():
    """Without FIREWALL_API_KEY env var, endpoints must remain open."""
    import app.api.routes as routes_mod
    # In test env, _FIREWALL_API_KEY should be None (not set)
    assert routes_mod._FIREWALL_API_KEY is None
    # Config endpoint should work without any key header
    res = client.post("/galaxy/config", json={
        "excitation_threshold": 150,
        "noise_tolerance": 0.005,
        "cosine_threshold": 0.78,
    })
    assert res.status_code == 200

def test_disabled_filter_skipped_in_pipeline():
    """A disabled filter must not appear in the pipeline trace."""
    cfg = ConfigState(
        cosine_threshold=0.0, excitation_threshold=0, global_noise_limit=10.0,
        noise_enabled=False  # Noise disabled
    )
    vec = np.random.rand(1024).astype(np.float32)
    result = SemanticFirewall.evaluate_clause(vec, vec, cfg, word_count=10)
    assert result["passed"] is True
    stage_names = [t["stage"] for t in result["trace"]]
    assert "noise" not in stage_names
    assert "cosine" in stage_names
    assert "excitation" in stage_names
    assert len(result["trace"]) == 2

def test_all_filters_disabled_bypasses_firewall():
    """With all filters disabled, pipeline is empty and clause passes trivially."""
    cfg = ConfigState(
        noise_enabled=False, cosine_enabled=False, excitation_enabled=False
    )
    vec = np.random.rand(1024).astype(np.float32)
    result = SemanticFirewall.evaluate_clause(vec, vec, cfg, word_count=10)
    assert result["passed"] is True
    assert len(result["trace"]) == 0

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

# Add pytest-asyncio to required pip if needed for async mark
