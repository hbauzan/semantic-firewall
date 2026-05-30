"""Security Tests — input validation, auth, injection prevention, path traversal.

Partitioned from perform_tests.py (Finding Q5).
Includes new tests for path traversal protection and Google API header auth.
"""
import pytest
from app.core.models import ChatRequest, PROMPT_MAX_LENGTH
from app.core.settings import settings
from tests.conftest import client


# --- Input Sanitization ---

def test_prompt_length_limit_rejected():
    """Prompts exceeding PROMPT_MAX_LENGTH must be rejected by Pydantic."""
    with pytest.raises(Exception):
        ChatRequest(prompt="x" * (PROMPT_MAX_LENGTH + 1))

def test_prompt_length_limit_accepted():
    """Prompts within PROMPT_MAX_LENGTH must be accepted."""
    req = ChatRequest(prompt="x" * PROMPT_MAX_LENGTH)
    assert len(req.prompt) == PROMPT_MAX_LENGTH


# --- API Key Auth ---

def test_api_key_not_enforced_by_default():
    """Without FIREWALL_API_KEY env var, endpoints must remain open."""
    assert settings.api_key_value is None
    res = client.post("/galaxy/config", json={
        "excitation_threshold": 150,
        "noise_tolerance": 0.005,
        "cosine_threshold": 0.78,
    })
    assert res.status_code == 200


# --- Provider Factory ---

def test_provider_factory_logic():
    """Verify that the factory correctly switches providers and fails fast."""
    from app.api.endpoints.chat import get_provider
    from app.modules.providers.ollama import OllamaProvider
    from app.modules.providers.google import GoogleGeminiProvider
    from app.core.settings import settings

    # Test Ollama Default
    original_provider = settings.upstream_provider
    settings.upstream_provider = "ollama"
    assert isinstance(get_provider(), OllamaProvider)

    # Test Google Fail-Fast
    settings.upstream_provider = "google"
    original_google_key = settings.google_api_key
    settings.google_api_key = None
    with pytest.raises(RuntimeError, match="Missing Google API Key"):
        get_provider()

    # Restore
    settings.upstream_provider = original_provider
    settings.google_api_key = original_google_key


# --- NEW: Path Traversal Protection (Finding S3) ---

def test_profile_path_traversal_rejected():
    """Profile names with path traversal sequences must be rejected."""
    from app.modules.profiles import ProfileManager, _SAFE_PROFILE_RE
    from app.core.models import ConfigState

    state = ConfigState()

    # Direct regex check
    assert not _SAFE_PROFILE_RE.match("../../etc/passwd")
    assert not _SAFE_PROFILE_RE.match("../secret")
    assert not _SAFE_PROFILE_RE.match("name with spaces")
    assert not _SAFE_PROFILE_RE.match("name.json")
    assert not _SAFE_PROFILE_RE.match("")
    assert not _SAFE_PROFILE_RE.match("a" * 65)  # too long

    # Valid names
    assert _SAFE_PROFILE_RE.match("valid_name")
    assert _SAFE_PROFILE_RE.match("valid-name-123")
    assert _SAFE_PROFILE_RE.match("_last_used")

    # ProfileManager methods must raise ValueError
    with pytest.raises(ValueError, match="Invalid profile name"):
        ProfileManager.save_profile("../../etc/passwd", state)

    with pytest.raises(ValueError, match="Invalid profile name"):
        ProfileManager.load_profile("../../../etc/shadow")

    with pytest.raises(ValueError, match="Invalid profile name"):
        ProfileManager.delete_profile("../../tmp/evil")


# --- NEW: Google API Key in Header (Finding S1) ---

def test_google_api_key_in_header():
    """Google provider must send API key via x-goog-api-key header, not URL query param."""
    import inspect
    from app.modules.providers.google import GoogleGeminiProvider

    source = inspect.getsource(GoogleGeminiProvider.stream_chat)

    # Must use header
    assert "x-goog-api-key" in source, "Google provider must use x-goog-api-key header"

    # Must NOT have key in URL query param
    assert "key={api_key}" not in source, "Google provider must NOT put key in URL query param"
    assert "key={}".format("api_key") not in source
