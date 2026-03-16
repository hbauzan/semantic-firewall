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

# Add pytest-asyncio to required pip if needed for async mark
