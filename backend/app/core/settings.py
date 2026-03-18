"""Centralized environment-driven settings — pydantic-settings (12-Factor).

All configuration is typed, validated, and loaded from environment variables
and/or a .env file at boot time. If a required variable is missing or has an
invalid type, the app crashes immediately with a clear Pydantic error.

Defaults match local development — zero .env file needed to run out of the box.
"""

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Single source of truth for all backend configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",  # ignore unknown vars in .env without crashing
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

    # --- Ollama ---
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Ollama API endpoint.",
    )
    ollama_model: str = Field(
        default="llama3.1",
        description="LLM model name for inference.",
    )

    # --- Embedding ---
    embedding_model: str = Field(
        default="BAAI/bge-m3",
        description="HuggingFace embedding model ID.",
    )

    # --- PDF Ingestion ---
    chunk_size: int = Field(default=2048, ge=100, le=10000)
    chunk_overlap: int = Field(default=200, ge=0, le=2000)
    embedding_batch_size: int = Field(default=10, ge=1, le=100)

    # --- Server ---
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000, ge=1, le=65535)
    reload: bool = Field(default=True)

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


# --- Singleton: instantiated once at import time (fail-fast) ---
settings = Settings()
