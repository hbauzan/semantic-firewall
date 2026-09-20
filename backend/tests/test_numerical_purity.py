"""TK-01 — Universal Numerical Purity & Decimal Truncation Remediation.

Invariants enforced by this module:

1. Zero ``round()`` / tensor-round ops in vector math, interval computation,
   or threshold sweeping.
2. Float-to-string conversions keep the full IEEE 754 mantissa
   (``f"{val:.17g}"`` or ``str(float(val))``), never fixed-decimal precision.
3. Embedding arrays are stored as ``float32``/``float64``, never ``float16``.
4. Coordinate separations of ``1e-5`` in the ``[-0.15, 0.15]`` magnitude band
   survive serialization and similarity scoring. Scalar similarity is computed
   in float64 — float32 accumulation collapses that gap to exactly 1.0, which
   would silently turn distinct concepts into identical scores.
"""
from __future__ import annotations

import ast
import json
import math
import re
from pathlib import Path

import numpy as np
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
APP_DIR = BACKEND_DIR / "app"

# Separations that the directive requires to remain strictly distinguishable.
MICRO_GAP = 1.0e-5
COORDINATE_BAND_LO = -0.15
COORDINATE_BAND_HI = 0.15


def _iter_source_files(root: Path) -> list[Path]:
    return sorted(
        p for p in root.rglob("*.py") if "__pycache__" not in p.parts
    )


def _strip_comments_and_docstrings(tree: ast.AST) -> ast.AST:
    """Drop docstrings so prose mentioning ``round()`` is not flagged."""
    for node in ast.walk(tree):
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            if isinstance(node.value.value, str):
                node.value.value = ""
    return tree


def _is_docstring(statement: ast.stmt) -> bool:
    return (
        isinstance(statement, ast.Expr)
        and isinstance(statement.value, ast.Constant)
        and isinstance(statement.value.value, str)
    )


def test_no_builtin_round_in_backend_app():
    """AST-level proof: the backend never calls Python's ``round()``."""
    offenders: list[str] = []
    for path in _iter_source_files(APP_DIR):
        tree = _strip_comments_and_docstrings(
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        )
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Name) and func.id == "round":
                offenders.append(f"{path.relative_to(BACKEND_DIR)}:{node.lineno}")
    assert not offenders, f"round() calls found: {offenders}"


def test_no_round_in_firewall_module():
    """TK-01 DoD — ``firewall.py`` must not call ``round()`` (or ``np.round``)."""
    source = (APP_DIR / "core" / "firewall.py").read_text(encoding="utf-8")
    tree = _strip_comments_and_docstrings(
        ast.parse(source, filename="app/core/firewall.py")
    )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Name) and func.id == "round":
            pytest.fail(f"builtin round() at firewall.py:{node.lineno}")
        if isinstance(func, ast.Attribute) and func.attr == "round":
            pytest.fail(f"tensor/numpy round() at firewall.py:{node.lineno}")


def test_no_numpy_or_torch_round_in_backend_app():
    offenders: list[str] = []
    for path in _iter_source_files(APP_DIR):
        tree = _strip_comments_and_docstrings(
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        )
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if isinstance(func, ast.Attribute) and func.attr == "round":
                offenders.append(f"{path.relative_to(BACKEND_DIR)}:{node.lineno}")
    assert not offenders, f"np/torch round() calls found: {offenders}"


def test_no_lossy_fixed_decimal_formatting_in_backend_app():
    """Any fixed-decimal float formatter destroys micro-gaps; banned."""
    pattern = re.compile(r"(:[0-9]*\.[0-9]+f|%[0-9]*\.[0-9]+f)")
    offenders: list[str] = []
    for path in _iter_source_files(APP_DIR):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if pattern.search(line):
                offenders.append(
                    f"{path.relative_to(BACKEND_DIR)}:{lineno}: {line.strip()}"
                )
    assert not offenders, f"lossy float formatting found: {offenders}"


def test_no_float16_downcast_in_backend_app():
    pattern = re.compile(
        r"\b(float16|bfloat16|Float16Array|\.half\(\)|astype\(\s*np\.float16)"
    )
    offenders: list[str] = []
    for path in _iter_source_files(APP_DIR):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if pattern.search(line):
                offenders.append(
                    f"{path.relative_to(BACKEND_DIR)}:{lineno}: {line.strip()}"
                )
    assert not offenders, f"float16 downcasts found: {offenders}"


# --- Behavioural purity: separations must survive every downstream stage ---


def _unit_vectors_with_gap(gap: float) -> tuple[np.ndarray, np.ndarray]:
    """Two unit vectors in the canonical embedding magnitude band."""
    rng = np.random.default_rng(20260920)
    base = rng.uniform(-0.15, 0.15, size=1024).astype(np.float32)
    base /= np.linalg.norm(base)
    shifted = base.copy()
    shifted[0] += gap
    shifted /= np.linalg.norm(shifted)
    return base, shifted


def test_vector_round_trip_is_bit_exact():
    """Embeddings survive an in-memory round trip without precision loss."""
    from app.modules.storage import pack_binary_signature

    vec = np.linspace(-0.15, 0.15, 1024, dtype=np.float32)
    stored = np.asarray(vec, dtype=np.float32)
    assert stored.dtype == np.float32
    np.testing.assert_array_equal(vec, stored)

    payload = [float(v) for v in stored.tolist()]
    restored = np.asarray(json.loads(json.dumps(payload)), dtype=np.float32)
    np.testing.assert_array_equal(stored, restored)

    packed = pack_binary_signature(stored)
    assert isinstance(packed, bytes)
    assert len(packed) == 128


def test_micro_gap_survives_similarity_scoring():
    """A 1e-5 coordinate gap must not collapse into an identical cosine score."""
    from app.core.firewall import SemanticFirewall
    from app.core.models import ConfigState

    a, b = _unit_vectors_with_gap(MICRO_GAP)
    assert a[0] != b[0]
    cfg = ConfigState()
    _, _, details_identical = SemanticFirewall.run_cosine_filter(a, a, cfg)
    _, _, details_a = SemanticFirewall.run_cosine_filter(b, a, cfg)
    sim_identical = details_identical["cosine_sim"]
    sim_a = details_a["cosine_sim"]
    assert sim_identical == 1.0
    assert sim_a < 1.0
    # The trailing gap is ~5e-11 for this synthetic pair; float32 accumulation
    # rounds both scores to exactly 1.0 and erases it entirely.
    assert 1.0 - sim_a > 1e-12
    assert math.floor(sim_identical * 1000.0) > math.floor(sim_a * 1000.0)


def test_micro_gap_survives_full_mantissa_serialization():
    """``:.17g`` keeps distinct floats distinct; fixed decimals would merge them."""
    lo = -0.0312
    hi = lo + MICRO_GAP
    assert lo != hi
    assert float(f"{lo:.17g}") != float(f"{hi:.17g}")
    # The 1e-5 gap is invisible to every fixed-decimal rendering up to 4 digits,
    # which is exactly how `:.4f` telemetry silently merges two coordinates.
    for decimals in range(1, 5):
        assert format(lo, f".{decimals}f") == format(hi, f".{decimals}f")
    # From 5 digits up the gap becomes observable again.
    assert format(lo, ".5f") != format(hi, ".5f")


def test_micro_gap_survives_normalization():
    a, b = _unit_vectors_with_gap(MICRO_GAP)
    assert a[0] != b[0]
    a32 = (np.asarray(a) / np.linalg.norm(a)).astype(np.float32)
    b32 = (np.asarray(b) / np.linalg.norm(b)).astype(np.float32)
    assert a32[0] != b32[0]


def test_sweep_grid_precision_is_not_decimal_truncated():
    """Grid points must be exact grid values, not decimal-round echoes."""
    from app.core.recommended_thresholds import (
        GLOBAL_EXCITATION_SWEEP,
        GLOBAL_COSINE_SWEEP,
        build_sweep_grid,
    )

    cosine = build_sweep_grid("cosine_threshold")
    lo = GLOBAL_COSINE_SWEEP["min"]
    step = GLOBAL_COSINE_SWEEP["step"]
    assert cosine[0] == pytest.approx(lo, rel=1e-12)
    for index, value in enumerate(cosine):
        expected = lo + index * step
        assert value == pytest.approx(expected, rel=1e-12), (
            f"grid sample {index} drifted from exact grid value"
        )

    excitation = build_sweep_grid("excitation_threshold")
    exc_lo = GLOBAL_EXCITATION_SWEEP["min"]
    exc_step = GLOBAL_EXCITATION_SWEEP["step"]
    for index, value in enumerate(excitation):
        assert value == pytest.approx(exc_lo + index * exc_step, rel=1e-12)

    noise = build_sweep_grid("global_noise_limit")
    for index, value in enumerate(noise):
        assert value == pytest.approx(noise[0] + index * 0.5, rel=1e-12)


def test_threshold_bounds_are_not_rounded_to_decimals():
    """Slider bounds derived from constants must stay exact floats."""
    from app.core.recommended_thresholds import (
        POSITIVE_RECOMMENDED,
        SLIDER_HALF_SPAN,
        slider_bounds,
    )

    for param, center in POSITIVE_RECOMMENDED.items():
        lo, hi, _step = slider_bounds(param)
        half = SLIDER_HALF_SPAN[param]
        assert lo == pytest.approx(center - half, rel=1e-15)
        assert hi == pytest.approx(center + half, rel=1e-15)


def test_calibration_summary_preserves_full_mantissa():
    """F1 / Youden reported by calibration must not be rounded to 4 decimals."""
    from app.modules.corpus_calibration import JointSweepPoint

    point = JointSweepPoint(
        cosine_threshold=0.5315,
        excitation_threshold=150,
        tp=7,
        fp=1,
        tn=9,
        fn=2,
    )
    assert point.f1 == 7 / (7 + 1) * 2 * (7 / 9) / (7 / 8 + 7 / 9)
    assert point.youden == pytest.approx(7 / 9 - 1 / 10, rel=1e-15)
    # Full-mantissa serialization must retain the exact ratio.
    payload = json.loads(json.dumps({"f1": point.f1, "youden": point.youden}))
    assert payload["f1"] == point.f1
    assert payload["youden"] == point.youden


def test_exceptions_render_full_mantissa():
    from app.core.exceptions import BurstDetectionBreach

    entropy = 2.9999991234567
    limit = 3.0
    exc = BurstDetectionBreach("clause", entropy, limit)
    assert f"{float(entropy):.17g}" in str(exc)
    assert f"{float(limit):.17g}" in str(exc)
    # Both renderings round-trip to the exact same IEEE 754 double.
    assert float(str(entropy)) == entropy
    assert float(f"{entropy:.17g}") == entropy


def test_block_message_tuning_hint_keeps_micro_gap_resolution():
    """Tuning hints are exported data, not cosmetic: no decimal truncation."""
    from app.api.endpoints.chat import _format_block_message
    from app.core.models import ConfigState

    cfg = ConfigState()
    traces = [
        {"stage": "noise", "passed": False, "entropy": 9.5485},
        {"stage": "cosine", "passed": False, "cosine_sim": 0.6538},
    ]
    msg = _format_block_message("test clause", "noise", {}, cfg, traces)
    assert "[TUNING HINT]" in msg
    cosine_target = math.floor(0.6538 * 1000.0) / 1000.0
    assert f"Cosine <= {float(cosine_target):.17g}" in msg
    assert "Cosine <= 0.653 " not in msg


# --- Regression: float32 scalar accumulation erases micro-gaps ---


def _trailing_gap_pair(gap: float) -> tuple[np.ndarray, np.ndarray]:
    """Two unit vectors differing only in the trailing mantissa digits.

    This mirrors the pathological case observed in production: two near-parallel
    high-dimensional vectors whose coordinate delta lives below float32's
    representable step (~6e-8) at the tail of the accumulation order.
    """
    rng = np.random.default_rng(20260920)
    base = rng.uniform(-0.15, 0.15, size=1024).astype(np.float32)
    base /= np.linalg.norm(base)
    shifted = base.copy()
    shifted[0] += gap
    shifted /= np.linalg.norm(shifted)
    return base, shifted


def test_trailing_micro_gap_is_erased_by_float32_scoring():
    """Documents the disease: float32 accumulation collapses the gap to 1.0."""
    a, b = _trailing_gap_pair(MICRO_GAP)
    a32 = a.astype(np.float32)
    b32 = b.astype(np.float32)
    sim32 = float(np.dot(b32, a32) / (np.linalg.norm(a32) * np.linalg.norm(b32)))
    assert sim32 == 1.0


def test_trailing_micro_gap_survives_float64_scoring():
    """The cure: float64 accumulation keeps the separation observable."""
    a, b = _trailing_gap_pair(MICRO_GAP)
    a64 = np.asarray(a, dtype=np.float64)
    b64 = np.asarray(b, dtype=np.float64)
    sim64 = float(np.dot(b64, a64) / (np.linalg.norm(b64) * np.linalg.norm(a64)))
    assert sim64 < 1.0
    assert 1.0 - sim64 > 1e-12
    assert sim64 != float(a64[0]) and 1.0 - sim64 < 1e-9


def test_precision_pair_constant_tracks_machine_epsilon():
    """The safety window must scale with float32 epsilon, not a magic constant."""
    from app.core.firewall import PRECISION_EPSILON_TOLERANCE, SIMILARITY_DTYPE

    assert SIMILARITY_DTYPE is np.float64
    assert PRECISION_EPSILON_TOLERANCE >= float(np.finfo(np.float32).eps)


def test_all_similarity_helpers_compute_in_float64():
    """Every RAG/similarity helper must upcast before the dot product."""
    targets = (
        APP_DIR / "modules" / "dataset_generator.py",
        APP_DIR / "modules" / "corpus_calibration.py",
    )
    helpers = {"_cosine_sim", "_rag_context_similarity"}
    checked = 0
    for path in targets:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.FunctionDef) or node.name not in helpers:
                continue
            checked += 1
            body = [statement for statement in node.body if not _is_docstring(statement)]
            segment = ast.unparse(ast.Module(body=body, type_ignores=[]))
            assert "float32" not in segment, (
                f"{path.name}:{node.name} still accumulates in float32"
            )
            assert "float64" in segment, (
                f"{path.name}:{node.name} does not upcast to float64"
            )
    assert checked == 2, f"expected 2 similarity helpers, inspected {checked}"
