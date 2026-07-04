"""Centralized environment-driven settings — pydantic-settings (12-Factor).

All configuration is typed, validated, and loaded from environment variables
and/or a .env file at boot time. If a required variable is missing or has an
invalid type, the app crashes immediately with a clear Pydantic error.

Defaults match local development — zero .env file needed to run out of the box.
"""

from typing import Literal
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


import os
from pathlib import Path

# Calculate the root path of the repository:
# settings.py -> core -> app -> backend -> project_root
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

class Settings(BaseSettings):
    """Single source of truth for all backend configuration."""

    model_config = SettingsConfigDict(
        env_file=str(ENV_PATH),           # absolute path to the project root `.env`
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown VITE_* etc. without crashing
    )

    # --- CORS ---
    allowed_origins: str = Field(
        default="http://localhost:5173",
        description="Comma-separated list of allowed CORS origins. Use * for dev only.",
    )

    # --- API Key (opt-in) ---
    firewall_api_key: SecretStr | None = Field(
        default=None,
        description="If set, /chat, /audit, /galaxy/config require X-API-Key header.",
    )

    # --- Upstream Provider Selection ---
    upstream_provider: Literal["ollama", "google", "openai", "anthropic", "groq"] = Field(
        default="ollama",
        description="Select the upstream LLM engine.",
    )

    # --- Google Gemini ---
    google_api_key: SecretStr | None = Field(
        default=None,
        description="Required if upstream_provider is 'google'.",
    )
    gemini_model_id: str = Field(
        default="gemini-2.5-pro",
        description="Google Gemini model identifier.",
    )

    # --- Ollama ---
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API endpoint.",
    )
    ollama_model: str = Field(
        default="llama3.1",
        description="LLM model name for inference.",
    )

    # --- OpenAI ---
    openai_api_key: SecretStr | None = Field(
        default=None,
        description="Required if upstream_provider is 'openai'.",
    )
    openai_model: str = Field(
        default="gpt-4o-mini",
        description="OpenAI model identifier.",
    )

    # --- Anthropic ---
    anthropic_api_key: SecretStr | None = Field(
        default=None,
        description="Required if upstream_provider is 'anthropic'.",
    )
    anthropic_model: str = Field(
        default="claude-3-5-sonnet-latest",
        description="Anthropic model identifier.",
    )

    # --- Groq ---
    groq_api_key: SecretStr | None = Field(
        default=None,
        description="Required if upstream_provider is 'groq'.",
    )
    groq_model: str = Field(
        default="llama-3.3-70b-versatile",
        description="Groq model identifier.",
    )

    # --- Embedding ---
    embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="HuggingFace embedding model ID.",
    )

    # --- RAG ---
    rag_top_k: int = Field(
        default=12, ge=1, le=32,
        description="Number of corpus chunks retrieved per clause for RAG context (1–32).",
    )

    # --- PDF Ingestion ---
    max_upload_mb: int = Field(
        default=50, ge=1, le=500,
        description="Maximum PDF upload size in megabytes.",
    )
    chunk_size: int = Field(default=512, ge=100, le=10000)  # Reduced for density
    chunk_overlap: int = Field(default=50, ge=0, le=2000)   # Reduced for precision
    embedding_batch_size: int = Field(default=10, ge=1, le=100)

    @property
    def max_upload_bytes(self) -> int:
        """Convert MB setting to bytes for upload validation."""
        return self.max_upload_mb * 1024 * 1024

    # --- Rate Limiting ---
    rate_limit_chat: str = Field(
        default="30/minute",
        description="Rate limit for /chat endpoint per client IP.",
    )
    rate_limit_default: str = Field(
        default="60/minute",
        description="Rate limit for all other endpoints per client IP.",
    )
    rate_limit_upload: str = Field(
        default="10/minute",
        description="Rate limit for /corpus/upload-pdf per client IP.",
    )

    # --- Server ---
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = Field(default=False)

    # --- Derived helpers (not env vars) ---

    @property
    def allowed_origins_list(self) -> list[str]:
        """Parse comma-separated origins string into a list."""
        return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]

    @property
    def credentials_allowed(self) -> bool:
        """allow_credentials=True is only safe with explicit origins, never with *."""
        return "*" not in self.allowed_origins_list

    @property
    def api_key_value(self) -> str | None:
        """Unwrap SecretStr for comparison. Returns None if unset."""
        return self.firewall_api_key.get_secret_value() if self.firewall_api_key else None

    @property
    def google_key_value(self) -> str | None:
        return self.google_api_key.get_secret_value() if self.google_api_key else None

    @property
    def openai_key_value(self) -> str | None:
        return self.openai_api_key.get_secret_value() if self.openai_api_key else None

    @property
    def anthropic_key_value(self) -> str | None:
        return self.anthropic_api_key.get_secret_value() if self.anthropic_api_key else None

    @property
    def groq_key_value(self) -> str | None:
        return self.groq_api_key.get_secret_value() if self.groq_api_key else None


# --- Singleton: instantiated once at import time (fail-fast) ---
settings = Settings()
