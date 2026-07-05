"""Tests for recommended threshold constants and sweep grid shape."""
from app.core.recommended_thresholds import (
    POSITIVE_RECOMMENDED,
    SLIDER_HALF_SPAN,
    SWEEP_GRIDS,
    build_data_driven_grids,
    build_sweep_grid,
    slider_bounds,
    threshold_2d_grid_size,
)


def test_sweep_grids_span_wider_than_hud_sliders():
    for param, center in POSITIVE_RECOMMENDED.items():
        if param == "global_noise_limit":
            continue
        grid = SWEEP_GRIDS[param]
        lo, hi, _step = slider_bounds(param)
        assert min(grid) <= lo
        assert max(grid) >= hi


def test_slider_bounds_center_on_recommended():
    for param, center in POSITIVE_RECOMMENDED.items():
        lo, hi, _step = slider_bounds(param)
        mid = (lo + hi) / 2
        assert abs(mid - center) < 1e-9


def test_excitation_sweep_extends_to_zero():
    grid = build_sweep_grid("excitation_threshold")
    assert min(grid) == 0
    assert max(grid) >= POSITIVE_RECOMMENDED["excitation_threshold"]


def test_cosine_sweep_has_fine_steps():
    grid = build_sweep_grid("cosine_threshold")
    assert len(grid) >= 25
    assert 0.53 in grid or any(abs(v - 0.53) < 0.03 for v in grid)


def test_2d_grid_pair_count():
    n_cos, n_exc = threshold_2d_grid_size()
    assert n_cos * n_exc == (
        len(SWEEP_GRIDS["cosine_threshold"])
        * len(SWEEP_GRIDS["excitation_threshold"])
    )


def test_data_driven_grids_from_cached_rows():
    cached_rows = [
        {
            "expected": "pass",
            "clauses": [{"has_context": True, "cosine_sim": 0.62, "activations": 160}],
        },
        {
            "expected": "block",
            "clauses": [{"has_context": True, "cosine_sim": 0.35, "activations": 90}],
        },
    ]
    grids = build_data_driven_grids(cached_rows)
    assert min(grids["cosine_threshold"]) <= 0.35
    assert max(grids["cosine_threshold"]) >= 0.62
    assert min(grids["excitation_threshold"]) <= 90
    assert max(grids["excitation_threshold"]) >= 160
