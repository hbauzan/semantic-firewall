"""Youden-derived recommended thresholds and calibration sweep grids.

Positive-mode recommendations are the center of HUD slider ranges and of
fallback sweep grids so optima are not searched at grid edges.
"""
from __future__ import annotations

import numpy as np

# Phase 2.1 Youden defaults (positive / negative allowlist-denylist)
POSITIVE_RECOMMENDED = {
    "cosine_threshold": 0.5315,
    "excitation_threshold": 150,
    "global_noise_limit": 4.5,
}

NEGATIVE_RECOMMENDED = {
    "cosine_threshold": 0.6197,
    "excitation_threshold": 170,
    "global_noise_limit": 4.5,
}

# HUD slider half-spans — recommended value sits at the midpoint
SLIDER_HALF_SPAN = {
    "cosine_threshold": 0.25,
    "excitation_threshold": 100,
    "global_noise_limit": 3.0,
}

SLIDER_STEP = {
    "cosine_threshold": 0.01,
    "excitation_threshold": 1,
    "global_noise_limit": 0.1,
}

# Wider global fallback grids (used when no cached metrics or sparse separation)
GLOBAL_COSINE_SWEEP = {
    "min": 0.20,
    "max": 0.80,
    "step": 0.02,
}
GLOBAL_EXCITATION_SWEEP = {
    "min": 0,
    "max": 300,
    "step": 10,
}


def slider_bounds(param: str) -> tuple[float, float, float]:
    """Return (min, max, step) centered on the positive recommended value."""
    center = POSITIVE_RECOMMENDED[param]
    half = SLIDER_HALF_SPAN[param]
    step = SLIDER_STEP[param]
    return center - half, center + half, step


def _float_grid(lo: float, hi: float, step: float) -> list[float]:
    values = np.arange(lo, hi + step * 0.5, step, dtype=np.float64)
    return [float(v) for v in values]


def _int_grid(lo: int, hi: int, step: int) -> list[int]:
    return list(range(int(lo), int(hi) + 1, int(step)))


def build_sweep_grid(param: str) -> list[float]:
    """Fallback 1D sweep grid — wider than HUD sliders, finer steps."""
    if param == "cosine_threshold":
        g = GLOBAL_COSINE_SWEEP
        return _float_grid(g["min"], g["max"], g["step"])
    if param == "excitation_threshold":
        g = GLOBAL_EXCITATION_SWEEP
        return [float(v) for v in _int_grid(g["min"], g["max"], g["step"])]
    if param == "global_noise_limit":
        center = POSITIVE_RECOMMENDED[param]
        values = np.arange(center - 3.0, center + 3.1, 0.5, dtype=np.float64)
        return [float(v) for v in values]
    raise KeyError(param)


SWEEP_GRIDS: dict[str, list[float]] = {
    "cosine_threshold": build_sweep_grid("cosine_threshold"),
    "excitation_threshold": build_sweep_grid("excitation_threshold"),
    "global_noise_limit": build_sweep_grid("global_noise_limit"),
}


def _clause_metrics_by_label(
    cached_rows: list[dict],
) -> tuple[list[float], list[float], list[int], list[int]]:
    """Return (pass_cos, block_cos, pass_exc, block_exc) per clause."""
    pass_cos: list[float] = []
    block_cos: list[float] = []
    pass_exc: list[int] = []
    block_exc: list[int] = []
    for row in cached_rows:
        for cl in row["clauses"]:
            if not cl["has_context"]:
                continue
            if row["expected"] == "pass":
                pass_cos.append(cl["cosine_sim"])
                pass_exc.append(cl["activations"])
            else:
                block_cos.append(cl["cosine_sim"])
                block_exc.append(cl["activations"])
    return pass_cos, block_cos, pass_exc, block_exc


def build_data_driven_grids(cached_rows: list[dict]) -> dict[str, list[float]]:
    """Build cosine×excitation grids from measured clause metrics.

    Spans the empirical separation zone with fine steps and merges the wider
    global fallback so edge optima are not missed.
    """
    pass_cos, block_cos, pass_exc, block_exc = _clause_metrics_by_label(cached_rows)
    if not pass_cos and not block_cos:
        return {
            "cosine_threshold": SWEEP_GRIDS["cosine_threshold"],
            "excitation_threshold": SWEEP_GRIDS["excitation_threshold"],
        }

    if block_cos and pass_cos:
        cos_lo = max(0.0, min(block_cos) - 0.08)
        cos_hi = min(1.0, max(pass_cos) + 0.08)
    else:
        center = POSITIVE_RECOMMENDED["cosine_threshold"]
        cos_lo, cos_hi = center - 0.20, center + 0.20

    cos_lo = min(cos_lo, GLOBAL_COSINE_SWEEP["min"])
    cos_hi = max(cos_hi, GLOBAL_COSINE_SWEEP["max"])
    data_cos = set(_float_grid(cos_lo, cos_hi, 0.02))

    if block_exc and pass_exc:
        exc_lo = max(0, min(block_exc) - 20)
        exc_hi = max(pass_exc) + 20
    else:
        center = POSITIVE_RECOMMENDED["excitation_threshold"]
        exc_lo, exc_hi = center - 125, center + 125

    exc_lo = min(exc_lo, GLOBAL_EXCITATION_SWEEP["min"])
    exc_hi = max(exc_hi, GLOBAL_EXCITATION_SWEEP["max"])
    data_exc = set(float(v) for v in _int_grid(exc_lo, exc_hi, 10))

    cosine = sorted(data_cos | set(SWEEP_GRIDS["cosine_threshold"]))
    excitation = sorted(data_exc | set(SWEEP_GRIDS["excitation_threshold"]))
    return {"cosine_threshold": cosine, "excitation_threshold": excitation}


def cosine_excitation_2d_grid_size(
    grids: dict[str, list[float]] | None = None,
) -> tuple[int, int]:
    """Return (n_cosine, n_excitation) for the joint 2D sweep."""
    g = grids or SWEEP_GRIDS
    return len(g["cosine_threshold"]), len(g["excitation_threshold"])


def threshold_2d_grid_size(grids: dict[str, list[float]] | None = None) -> tuple[int, int]:
    """Return (n_cosine, n_excitation) for the joint calibration sweep."""
    return cosine_excitation_2d_grid_size(grids)


def threshold_3d_grid_size() -> tuple[int, int, int]:
    """Legacy 3D size helper — noise is no longer swept; third dim is 1."""
    n_cos, n_exc = threshold_2d_grid_size()
    return n_cos, n_exc, 1
