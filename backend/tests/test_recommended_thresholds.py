"""Tests for recommended threshold constants and sweep grid shape."""
from app.core.recommended_thresholds import (
    POSITIVE_RECOMMENDED,
    SLIDER_HALF_SPAN,
    SWEEP_GRIDS,
    build_sweep_grid,
    slider_bounds,
)


def test_sweep_grids_are_centered_on_positive_recommended():
    for param, center in POSITIVE_RECOMMENDED.items():
        grid = SWEEP_GRIDS[param]
        assert min(grid) < center < max(grid)
        assert center in grid or abs(min(grid, key=lambda v: abs(v - center)) - center) <= (
            0.05 if param == "cosine_threshold" else 25 if param == "excitation_threshold" else 0.5
        )


def test_slider_bounds_center_on_recommended():
    for param, center in POSITIVE_RECOMMENDED.items():
        lo, hi, _step = slider_bounds(param)
        mid = (lo + hi) / 2
        assert abs(mid - center) < 1e-9


def test_excitation_sweep_extends_below_old_minimum():
    grid = build_sweep_grid("excitation_threshold")
    assert min(grid) < 75
    assert POSITIVE_RECOMMENDED["excitation_threshold"] in grid


def test_3d_grid_triple_count():
    from app.core.recommended_thresholds import threshold_3d_grid_size

    n_cos, n_exc, n_noise = threshold_3d_grid_size()
    assert n_cos * n_exc * n_noise == (
        len(SWEEP_GRIDS["cosine_threshold"])
        * len(SWEEP_GRIDS["excitation_threshold"])
        * len(SWEEP_GRIDS["global_noise_limit"])
    )
