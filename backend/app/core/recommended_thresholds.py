"""Youden-derived recommended thresholds and calibration sweep grids.

Positive-mode recommendations are the center of HUD slider ranges and of
1D sweep grids so optima are not searched at grid edges.
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


def slider_bounds(param: str) -> tuple[float, float, float]:
    """Return (min, max, step) centered on the positive recommended value."""
    center = POSITIVE_RECOMMENDED[param]
    half = SLIDER_HALF_SPAN[param]
    step = SLIDER_STEP[param]
    return center - half, center + half, step


def build_sweep_grid(param: str) -> list[float]:
    """1D sweep grid centered on positive recommended; extends beyond slider range."""
    center = POSITIVE_RECOMMENDED[param]
    if param == "cosine_threshold":
        values = np.arange(center - 0.20, center + 0.21, 0.05)
        return [round(float(v), 2) for v in values]
    if param == "excitation_threshold":
        return list(range(int(center - 125), int(center + 126), 25))
    if param == "global_noise_limit":
        values = np.arange(center - 3.0, center + 3.1, 0.5)
        return [round(float(v), 1) for v in values]
    raise KeyError(param)


SWEEP_GRIDS: dict[str, list[float]] = {
    "cosine_threshold": build_sweep_grid("cosine_threshold"),
    "excitation_threshold": build_sweep_grid("excitation_threshold"),
    "global_noise_limit": build_sweep_grid("global_noise_limit"),
}


def cosine_excitation_2d_grid_size() -> tuple[int, int]:
    """Return (n_cosine, n_excitation) for the joint 2D sweep."""
    return len(SWEEP_GRIDS["cosine_threshold"]), len(SWEEP_GRIDS["excitation_threshold"])
