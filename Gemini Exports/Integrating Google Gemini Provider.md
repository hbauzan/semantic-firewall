# Chat Conversation

Note: _This is purely the output of the chat conversation and does not contain any raw data, codebase snippets, etc. used to generate the output._

### User Input

Acknowledged. Initializing SSA Protocol V-ALL.
The mission is to integrate Google Gemini Pro as an alternative upstream provider while maintaining the Full Payload Interception (FPI) and Semantic Firewall integrity.
1. MANIFEST UPDATE
code
JSON
{
    "project": "Three-Headed Semantic Firewall",
    "version": "v2.17.0",
    "active_features": {
        "google_gemini_provider": true,
        "dynamic_provider_factory": true,
        "upstream_provider_selection": true,
        "gemini_sse_normalization": true,
        "fail_fast_provider_validation": true
    }
}
2. ARCHITECTURE SPECIFICATION UPDATE
Add to Section 9. Transparent Proxy Architecture:
9.1 Google Gemini Provider
Implements the BaseProvider interface for Google's Generative AI API.
Endpoint: v1beta/models/{model}:streamGenerateContent?alt=sse.
Normalization: Maps Gemini's candidates[0].content.parts[0].text structure into the OpenAI-compatible choices[0].delta.content SSE format.
Security: Requires GOOGLE_API_KEY. The system performs a fail-fast check at boot; if UPSTREAM_PROVIDER is set to google and the key is missing, the application terminates with a Critical log.
9.2 Provider Factory
The chat_endpoint and openai_proxy no longer instantiate providers directly. A factory pattern resolves the provider at runtime based on the UPSTREAM_PROVIDER environment variable. This ensures the Semantic Firewall remains provider-agnostic.
3. TECHNICAL IMPLEMENTATION
3.1 Settings Extension (backend/app/core/settings.py)
code
Python
# --- Upstream Provider Selection ---
    upstream_provider: Literal["ollama", "google"] = Field(
        default="ollama",
        description="Select the upstream LLM engine.",
    )

    # --- Google Gemini ---
    google_api_key: SecretStr | None = Field(
        default=None,
        description="Required if upstream_provider is 'google'.",
    )
    gemini_model_id: str = Field(
        default="gemini-1.5-pro",
        description="Google Gemini model identifier.",
    )

    @property
    def google_key_value(self) -> str | None:
        return self.google_api_key.get_secret_value() if self.google_api_key else None
3.2 Google Provider (backend/app/modules/providers/google.py)
code
Python
import json
import httpx
from typing import AsyncGenerator
from app.modules.providers.base import BaseProvider
from app.core.settings import settings

class GoogleGeminiProvider(BaseProvider):
    async def stream_chat(self, model: str, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        api_key = settings.google_key_value
        model_id = settings.gemini_model_id
        
        # Gemini expects a specific 'contents' format
        contents = []
        for m in messages:
            role = "user" if m["role"] == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m["content"]}]})

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:streamGenerateContent?alt=sse&key={api_key}"
        
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, read=300.0)) as client:
            async with client.stream("POST", url, json={"contents": contents}) as response:
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            data = json.loads(line[6:])
                            # Extract text from Gemini structure
                            text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                            if text:
                                yield f"data: {json.dumps({'choices': [{'delta': {'content': text}, 'finish_reason': None}]})}\n\n"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            continue
                yield "data: [DONE]\n\n"
3.3 Provider Factory & Fail-Fast (backend/app/api/routes.py)
code
Python
from app.modules.providers.ollama import OllamaProvider
from app.modules.providers.google import GoogleGeminiProvider

def get_provider():
    if settings.upstream_provider == "google":
        if not settings.google_key_value:
            logger.critical("UPSTREAM_PROVIDER set to 'google' but GOOGLE_API_KEY is missing.")
            raise RuntimeError("Missing Google API Key")
        return GoogleGeminiProvider()
    return OllamaProvider()

provider = get_provider()
4. TESTING SOVEREIGNTY (backend/perform_tests.py)
Add this test function to verify the factory and provider mapping:
code
Python
@pytest.mark.asyncio
async def test_provider_factory_logic():
    """Verify that the factory correctly switches providers and fails fast."""
    from app.api.routes import get_provider
    from app.modules.providers.ollama import OllamaProvider
    from app.modules.providers.google import GoogleGeminiProvider
    from app.core.settings import settings
    
    # Test Ollama Default
    settings.upstream_provider = "ollama"
    assert isinstance(get_provider(), OllamaProvider)
    
    # Test Google Fail-Fast
    settings.upstream_provider = "google"
    settings.firewall_api_key = None # Ensure no key is set
    with pytest.raises(RuntimeError, match="Missing Google API Key"):
        get_provider()
5. MANDATORY EXECUTION DIRECTIVE
To the Programming Agent:
Implement the changes in settings.py, google.py, and routes.py.
Execute pytest backend/perform_tests.py.
Validation Loop: If the tests fail or the v1/chat/completions endpoint returns a 500 error when using the Google provider, you MUST inspect the httpx stream logs, adjust the JSON parsing logic in GoogleGeminiProvider, and re-run tests until a successful 200 OK SSE stream is achieved.
FPI Check: Verify that the SnifferTab correctly reconstructs the Gemini response. If the sniffer shows empty content, adjust the stream_wrapper in routes.py to match the normalized SSE output.
[SYSTEM SYNC COMPLETE - READY FOR DEPLOYMENT]

*Edited relevant file*

*Viewed [manifest.json](file:///Users/hbauzan/treepwood/semantic-firewall/manifest.json) *

*Viewed [architecture_spec.md](file:///Users/hbauzan/treepwood/semantic-firewall/architecture_spec.md) *

*Viewed [settings.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/core/settings.py) *

*Viewed [routes.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/api/routes.py) *

*Viewed [perform_tests.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/perform_tests.py) *

*Viewed [base.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/modules/providers/base.py) *

*Viewed [ollama.py](file:///Users/hbauzan/treepwood/semantic-firewall/backend/app/modules/providers/ollama.py) *

*Edited relevant file*

*Edited relevant file*

### User Input

This is a system-generated message that is sent due to the user's review policy. Proceed with the decision that you think is the most optimal here.

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

*Edited relevant file*

*User accepted the command `PYTHONPATH=. pytest backend/perform_tests.py`*

*Checked command status*

*Checked command status*

*Checked command status*

*Edited relevant file*

*Edited relevant file*