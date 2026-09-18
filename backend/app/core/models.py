"""Pydantic models for the Semantic Firewall configuration and API contracts.

All schema validation, field constraints, and business rules live here.
Zero framework dependencies — portable across FastAPI, CLI, or any runtime.
"""
from typing import Literal
from pydantic import BaseModel, Field, model_validator, ConfigDict


class ConfigState(BaseModel):
    """Immutable firewall configuration snapshot.

    Frozen after construction — any update creates a new instance.
    The model_validator enforces that pipeline order values are always unique.
    """
    model_config = ConfigDict(frozen=True)

    excitation_threshold: int = Field(default=150, ge=0, le=1024)
    noise_tolerance: float = Field(default=0.005, ge=0.0, le=1.0)
    # Optimized Youden Threshold (0.5315) for Negative Mode default
    cosine_threshold: float = Field(default=0.5315, ge=0.0, le=1.0)
    # Global Noise Limit — Shannon Entropy Floor (corpus-independent, embedding space)
    global_noise_limit: float = Field(default=4.5, ge=0.0, le=10.0)
    # Raw character entropy floor — CPU pre-filter before embedding (character scale ~0–5)
    raw_entropy_limit: float = Field(default=3.0, ge=0.0, le=10.0)
    cosine_order: int = Field(default=1, ge=1, le=3)
    excitation_order: int = Field(default=3, ge=1, le=3)
    noise_order: int = Field(default=2, ge=1, le=3)
    adaptive_factor: float = Field(default=0.85, ge=0.01, le=1.0)
    rag_top_k: int = Field(default=12, ge=1, le=32)
    sniffer_view_limit: int = Field(default=10, ge=1, le=1000)
    noise_enabled: bool = Field(default=True)
    cosine_enabled: bool = Field(default=True)
    excitation_enabled: bool = Field(default=True)
    firewall_mode: Literal["positive", "negative"] = Field(
        default="positive",
        description=(
            "positive: only corpus-aligned queries pass (allowlist). "
            "negative: corpus-aligned queries are blocked (denylist)."
        ),
    )
    active_tab: str = Field(
        default="chat",
        description="Last active UI tab. Persisted to _last_used profile for session continuity.",
    )
    upstream_provider: Literal["ollama", "google", "openai", "anthropic", "groq"] = Field(
        default="ollama",
        description="Active Upstream LLM Provider",
    )
    active_corpus_file: str | None = Field(
        default=None,
        description=(
            "Pack filename for pack-scoped RAG/firewall search. "
            "When null and exactly one pack is loaded, that pack is used automatically."
        ),
    )
    calibration_coverage: Literal["fast", "recommended", "exhaustive"] = Field(
        default="recommended",
        description="Dataset coverage mode for automatic corpus calibration",
    )
    egress_profile: Literal["chat", "compliance"] = Field(
        default="chat",
        description=(
            "chat: freeze generation on `. ; ?` or newline, evaluate, burst or cut. "
            "compliance: hold the full response and audit DLP/homoglyphs/INLP/numbers/AND "
            "before any generation token reaches the client. CDE must set compliance."
        ),
    )

    @model_validator(mode='after')
    def validate_unique_orders(self):
        orders = {self.cosine_order, self.excitation_order, self.noise_order}
        if len(orders) != 3:
            raise ValueError(
                'Pipeline order values must be unique (each of 1, 2, 3). '
                f'Got cosine={self.cosine_order}, excitation={self.excitation_order}, noise={self.noise_order}'
            )
        return self


class ConfigUpdate(BaseModel):
    """Inbound payload for POST /galaxy/config. Validated on arrival."""
    excitation_threshold: int = Field(ge=0, le=1024)
    noise_tolerance: float = Field(ge=0.0, le=1.0)
    cosine_threshold: float = Field(ge=0.0, le=1.0)
    global_noise_limit: float = Field(default=4.5, ge=0.0, le=10.0)
    raw_entropy_limit: float = Field(default=3.0, ge=0.0, le=10.0)
    cosine_order: int = Field(default=1, ge=1, le=3)
    excitation_order: int = Field(default=3, ge=1, le=3)
    noise_order: int = Field(default=2, ge=1, le=3)
    adaptive_factor: float = Field(default=0.85, ge=0.01, le=1.0)
    rag_top_k: int = Field(default=12, ge=1, le=32)
    sniffer_view_limit: int = Field(default=10, ge=1, le=1000)
    noise_enabled: bool = Field(default=True)
    cosine_enabled: bool = Field(default=True)
    excitation_enabled: bool = Field(default=True)
    firewall_mode: Literal["positive", "negative"] = Field(default="positive")
    active_tab: str = Field(default="chat")
    upstream_provider: Literal["ollama", "google", "openai", "anthropic", "groq"] = Field(default="ollama")
    active_corpus_file: str | None = Field(default=None)
    calibration_coverage: Literal["fast", "recommended", "exhaustive"] = Field(default="recommended")
    egress_profile: Literal["chat", "compliance"] = Field(default="chat")


# Max prompt length to prevent memory exhaustion before vectorization
PROMPT_MAX_LENGTH = 4000


class AuditRequest(BaseModel):
    query: str = Field(max_length=PROMPT_MAX_LENGTH)


class ChatRequest(BaseModel):
    prompt: str = Field(max_length=PROMPT_MAX_LENGTH)


class OpenAIMessage(BaseModel):
    role: str
    content: str


class OpenAIConfig(BaseModel):
    model: str
    messages: list[OpenAIMessage]
    stream: bool = False
    temperature: float = 0.7
