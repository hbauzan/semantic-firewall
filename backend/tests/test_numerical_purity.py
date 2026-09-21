"""IEEE 754 full-mantissa locks for coordinates, telemetry, and sweep grids.

Truncation at 4 decimal places merges embedding coordinates that sit 1e-5 apart.
These tests pin the decision path to native float32/float64 text and storage.
"""
from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import numpy as np
import pyarrow as pa

from app.core.exceptions import BurstDetectionBreach
from app.core.firewall import SemanticFirewall
from app.core.models import ConfigState
from app.core.numerical import format_float
from app.core.recommended_thresholds import build_sweep_grid
from app.modules.storage import RABITQ_VECTOR_DIM, rabitq_schema

_APP = Path(__file__).resolve().parents[1] / "app"
_SCAN_ROOTS = (_APP / "core", _APP / "modules")
_EXTRA_SOURCES = (_APP / "api" / "endpoints" / "chat.py",)
_ROUND_CALL = re.compile(r"\b(?:round|np\.round|numpy\.round|torch\.round)\s*\(")
_FIXED_DECIMAL = re.compile(r"[:%][0-9]*\.[0-9]+f")
_HALF_PRECISION = re.compile(r"\b(?:float16|bfloat16)\b|\.half\(\)")

_MICRO_GAP = 1.0e-5
_COORD_A = np.float32(0.02438219)
_COORD_B = np.float32(_COORD_A + np.float32(_MICRO_GAP))


def _python_sources() -> list[Path]:
    files: list[Path] = []
    for root in _SCAN_ROOTS:
        files.extend(sorted(root.rglob("*.py")))
    files.extend(_EXTRA_SOURCES)
    return files


def _code_lines(path: Path) -> list[tuple[int, str]]:
    lines: list[tuple[int, str]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if line.strip().startswith("#"):
            continue
        lines.append((number, line))
    return lines


def test_float32_vector_roundtrip_is_bit_exact():
    rng = np.random.default_rng(7)
    original = rng.normal(loc=0.0, scale=0.03125, size=RABITQ_VECTOR_DIM).astype(np.float32)

    as_text = [format_float(component) for component in original.tolist()]
    from_text = np.asarray([float(token) for token in as_text], dtype=np.float32)

    as_json = json.loads(json.dumps(original.tolist()))
    from_json = np.asarray(as_json, dtype=np.float32)

    arrow = pa.array(original, type=pa.float32())
    from_arrow = np.asarray(arrow.to_pylist(), dtype=np.float32)

    np.testing.assert_array_equal(from_text.view(np.uint32), original.view(np.uint32))
    np.testing.assert_array_equal(from_json.view(np.uint32), original.view(np.uint32))
    np.testing.assert_array_equal(from_arrow.view(np.uint32), original.view(np.uint32))


def test_microgap_coordinates_stay_separated():
    assert float(_COORD_B) > float(_COORD_A)
    assert round(float(_COORD_A), 4) == round(float(_COORD_B), 4)

    text_a = format_float(_COORD_A)
    text_b = format_float(_COORD_B)
    assert float(text_b) > float(text_a)

    q = np.zeros(RABITQ_VECTOR_DIM, dtype=np.float32)
    c = np.zeros(RABITQ_VECTOR_DIM, dtype=np.float32)
    q[0] = _COORD_A
    c[0] = _COORD_B
    q[1] = np.float32(0.5)
    c[1] = np.float32(0.5)

    delta0 = float(np.abs(q - c)[0])
    assert 0.0 < delta0 < 1.0e-4

    cfg = ConfigState(
        noise_tolerance=1.0e-6,
        excitation_threshold=RABITQ_VECTOR_DIM,
        cosine_threshold=0.0,
        global_noise_limit=0.0,
    )
    passed, _stage, details = SemanticFirewall.run_excitation_filter(q, c, cfg, word_count=8)
    assert details["activations"] == RABITQ_VECTOR_DIM - 1
    assert passed is False


def test_breach_telemetry_keeps_entropy_microgap():
    base = 2.500014
    low = BurstDetectionBreach("clause", base, 4.5)
    high = BurstDetectionBreach("clause", base + _MICRO_GAP, 4.5)
    assert f"{base:.4f}" == f"{base + _MICRO_GAP:.4f}"
    assert str(low) != str(high)
    assert format_float(base) in str(low)
    assert format_float(base + _MICRO_GAP) in str(high)


def test_chat_block_telemetry_keeps_entropy_microgap():
    from app.api.endpoints.chat import _format_block_message

    cfg = ConfigState()
    base = 2.500014

    def traces(entropy: float) -> list[dict]:
        return [{"stage": "noise", "passed": False, "entropy": entropy}]

    low = _format_block_message("clause", "noise", {}, cfg, traces(base))
    high = _format_block_message("clause", "noise", {}, cfg, traces(base + _MICRO_GAP))
    assert low != high
    assert format_float(base) in low
    assert format_float(base + _MICRO_GAP) in high


def test_threshold_json_preserves_microgap():
    low = ConfigState(cosine_threshold=float(_COORD_A))
    high = ConfigState(cosine_threshold=float(_COORD_B))
    low_value = json.loads(low.model_dump_json())["cosine_threshold"]
    high_value = json.loads(high.model_dump_json())["cosine_threshold"]
    assert high_value > low_value
    assert high_value - low_value >= _MICRO_GAP * 0.5


def test_lancedb_vector_column_is_float32():
    vector_field = rabitq_schema.field("vector")
    assert pa.types.is_list(vector_field.type) or pa.types.is_fixed_size_list(vector_field.type)
    assert pa.types.is_float32(vector_field.type.value_type)
    assert vector_field.type.list_size == RABITQ_VECTOR_DIM


def test_cosine_sweep_grid_is_not_centi_quantized():
    grid = build_sweep_grid("cosine_threshold")
    assert any(value != round(value, 2) for value in grid)


def test_firewall_does_not_call_round():
    path = _APP / "core" / "firewall.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    hits: list[int] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "round":
            hits.append(node.lineno)
        elif isinstance(func, ast.Attribute) and func.attr == "round":
            hits.append(node.lineno)
    assert hits == []


def test_core_and_modules_have_no_truncation():
    violations: list[str] = []
    for path in _python_sources():
        rel = path.relative_to(_APP.parent)
        for number, line in _code_lines(path):
            if _ROUND_CALL.search(line) or _FIXED_DECIMAL.search(line) or _HALF_PRECISION.search(line):
                violations.append(f"{rel}:{number}:{line.strip()}")
    assert violations == []
