"""Shared dependencies for API endpoint modules.

Centralizes verify_api_key and limiter so all endpoint modules import
from a single location. Avoids circular imports and duplicate instances.
"""
import hmac
import logging
from fastapi import Header, HTTPException
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.settings import settings

logger = logging.getLogger(__name__)

# --- Rate Limiter (shared instance) ---
limiter = Limiter(key_func=get_remote_address)

# --- Optional API Key Guard ---

async def verify_api_key(x_api_key: str | None = Header(default=None)):
    """Opt-in API key check. Only enforced if FIREWALL_API_KEY env var is set.
    Uses hmac.compare_digest for constant-time comparison (timing-attack safe)."""
    api_key = settings.api_key_value
    if api_key:
        if not x_api_key or not hmac.compare_digest(x_api_key, api_key):
            raise HTTPException(status_code=403, detail="Invalid or missing API key")
