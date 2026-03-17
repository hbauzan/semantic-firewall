"""Pydantic models for the Semantic Firewall configuration and API contracts.

All schema validation, field constraints, and business rules live here.
Zero framework dependencies — portable across FastAPI, CLI, or any runtime.
"""
from pydantic import BaseModel, Field, model_validator, ConfigDict


class ConfigState(BaseModel):
    """Immutable firewall configuration snapshot.

    Frozen after construction — any update creates a new instance.
    The model_validator enforces that pipeline order values are always unique.
    """
    model_config = ConfigDict(frozen=True)

    excitation_threshold: int = Field(default=150, ge=0, le=1024)
    noise_tolerance: float = Field(default=0.005, ge=0.0, le=1.0)
    cosine_threshold: float = Field(default=0.50, ge=0.0, le=1.0)
    global_noise_limit: float = Field(default=0.50, ge=0.0, le=10.0)
    cosine_order: int = Field(default=2, ge=1, le=3)
    excitation_order: int = Field(default=3, ge=1, le=3)
    noise_order: int = Field(default=1, ge=1, le=3)
    adaptive_factor: float = Field(default=0.85, ge=0.01, le=1.0)
    noise_enabled: bool = Field(default=True)
    cosine_enabled: bool = Field(default=True)
    excitation_enabled: bool = Field(default=True)

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
    global_noise_limit: float = Field(default=0.50, ge=0.0, le=10.0)
    cosine_order: int = Field(default=2, ge=1, le=3)
    excitation_order: int = Field(default=3, ge=1, le=3)
    noise_order: int = Field(default=1, ge=1, le=3)
    adaptive_factor: float = Field(default=0.85, ge=0.01, le=1.0)
    noise_enabled: bool = Field(default=True)
    cosine_enabled: bool = Field(default=True)
    excitation_enabled: bool = Field(default=True)


# Max prompt length to prevent memory exhaustion before vectorization
PROMPT_MAX_LENGTH = 4000


class AuditRequest(BaseModel):
    query: str = Field(max_length=PROMPT_MAX_LENGTH)


class ChatRequest(BaseModel):
    prompt: str = Field(max_length=PROMPT_MAX_LENGTH)
