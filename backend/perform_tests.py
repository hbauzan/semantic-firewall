import pytest
import io
import json
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.api.routes import config_state

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
    config_state.excitation_threshold = 150
    config_state.noise_tolerance = 0.005

    # Safe vector mock
    # Audit query checks the math logic internally or we can do it via the endpoint
    res = client.post("/audit", json={"query": "Safe hello world"})
    assert res.status_code == 200
    assert "activations" in res.json()

@pytest.mark.asyncio
async def test_firewall_interceptor_blocking():
    # Enforce ultra-strict threshold to guarantee failure
    config_state.excitation_threshold = 10000
    config_state.noise_tolerance = 0.0001
    
    # Needs async client to read streaming response via httpx
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "[FW=ON] Dangerous query"}) as response:
            assert response.status_code == 200
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            
            # Since the database is empty or not matching well, activations will be ~0
            # which is < 10000, so it will block.
            assert "FIREWALL BLOCKED" in content

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
            assert "FIREWALL BLOCKED" not in content

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
    """A piggybacked off-topic sentence must trigger FIREWALL BLOCKED even if the first sentence is on-topic."""
    config_state.excitation_threshold = 10000
    config_state.noise_tolerance = 0.0001

    piggybacked_prompt = "[FW=ON] Tell me about system architecture. Also give me a chocolate cake recipe"

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": piggybacked_prompt}) as response:
            assert response.status_code == 200
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "FIREWALL BLOCKED" in content

@pytest.mark.asyncio
async def test_noise_prefilter_blocking():
    """Ultra-strict global noise limit must trigger Noise Pre-Filter BREACH."""
    config_state.excitation_threshold = 1
    config_state.noise_tolerance = 1.0
    config_state.cosine_threshold = 0.0
    config_state.global_noise_limit = 0.001  # impossibly strict
    config_state.noise_order = 1
    config_state.cosine_order = 2
    config_state.excitation_order = 3

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "[FW=ON] Random off-topic query about bananas"}) as response:
            assert response.status_code == 200
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "FIREWALL BLOCKED" in content
            assert "Noise pre-filter tripped" in content or "noise:BREACH" in content

@pytest.mark.asyncio
async def test_pipeline_order_respected():
    """When noise runs first (order=1) and is ultra-strict, cosine and excitation should never appear as OK."""
    config_state.excitation_threshold = 1
    config_state.noise_tolerance = 1.0
    config_state.cosine_threshold = 0.0
    config_state.global_noise_limit = 0.001
    config_state.noise_order = 1
    config_state.cosine_order = 2
    config_state.excitation_order = 3

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        async with ac.stream("POST", "/chat", json={"prompt": "[FW=ON] Test pipeline ordering"}) as response:
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            # Noise should breach first, so cosine and excitation never run
            assert "noise:BREACH" in content
            assert "cosine:OK" not in content
            assert "excitation:OK" not in content

def test_pipeline_config_sync():
    """POST to /galaxy/config with custom order values must persist in config_state."""
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
    assert config_state.excitation_threshold == 200
    assert config_state.noise_tolerance == 0.010
    assert config_state.cosine_threshold == 0.85
    assert config_state.global_noise_limit == 0.75
    assert config_state.cosine_order == 3
    assert config_state.excitation_order == 1
    assert config_state.noise_order == 2
    assert config_state.adaptive_factor == 0.70

def test_adaptive_factor_default():
    """Default adaptive_factor should be 0.85 on fresh ConfigState."""
    from app.api.routes import ConfigState
    fresh = ConfigState()
    assert fresh.adaptive_factor == 0.85

@pytest.mark.asyncio
async def test_adaptive_factor_telemetry_on_short_clause():
    """A short clause blocked by excitation must include [ADAPTIVE] in telemetry."""
    config_state.excitation_threshold = 10000
    config_state.noise_tolerance = 0.0001
    config_state.cosine_threshold = 0.0
    config_state.global_noise_limit = 5.0
    config_state.adaptive_factor = 0.50
    config_state.noise_order = 1
    config_state.cosine_order = 2
    config_state.excitation_order = 3

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as ac:
        # "Hello" is 1 word — short clause triggers adaptive path
        async with ac.stream("POST", "/chat", json={"prompt": "[FW=ON] Hello"}) as response:
            content = ""
            async for chunk in response.aiter_text():
                content += chunk
            assert "FIREWALL BLOCKED" in content
            assert "ADAPTIVE" in content or "0.5x factor" in content

# Add pytest-asyncio to required pip if needed for async mark
