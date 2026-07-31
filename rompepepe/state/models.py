"""Data schemas for rompepepe state tracking and telemetry serialization.
"""
from typing import Any, Literal
from pydantic import BaseModel, Field


class TelemetryTraceItem(BaseModel):
    filter: str
    order: int
    score: float
    threshold: float
    passed: bool
    details: dict[str, Any] = Field(default_factory=dict)


class TelemetryTrace(BaseModel):
    passed: bool
    breach_reason: str | None = None
    trace: list[TelemetryTraceItem] = Field(default_factory=list)
    activations: int = 0
    text: str = ""
    cosine_delta: float | None = None
    excitation_level: float | None = None
    noise_entropy: float | None = None


class TestResult(BaseModel):
    __test__ = False

    step: int
    prompt: str
    config: dict[str, Any]
    passed: bool
    breach_reason: str | None = None
    telemetry: TelemetryTrace
    duration_ms: float
    is_boundary_transition: bool = False
    notes: str = ""


class BoundaryTrace(BaseModel):
    step_a: int
    step_b: int
    prompt_a: str
    prompt_b: str
    passed_a: bool
    passed_b: bool
    cosine_a: float | None = None
    cosine_b: float | None = None
    mutation_description: str
    timestamp: str


class SessionState(BaseModel):
    session_id: str
    strategy: Literal["grid_search", "adaptive_fuzzing"]
    status: Literal["running", "paused", "completed", "interrupted"] = "running"
    created_at: str
    updated_at: str
    total_steps: int = 0
    current_step: int = 0
    config_grid: list[dict[str, Any]] = Field(default_factory=list)
    results: list[TestResult] = Field(default_factory=list)
    boundary_traces: list[BoundaryTrace] = Field(default_factory=list)
    initial_target_config: dict[str, Any] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)
