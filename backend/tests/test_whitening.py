"""L02 — whitening lab (pure geometry). Does not call evaluate_clause."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.modules.geometry.whitening import (
    MIN_SAMPLES,
    WhiteningModel,
    demo_sliding_windows,
    dense_matrix_from_rows,
    fit_whitening,
    load_demo_corpus_body,
    load_whitening,
    save_whitening,
    sliding_windows,
    whiten,
)


def _correlated_corpus(n: int, d: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    mean = rng.normal(2.0, 0.5, size=d)
    scale = rng.uniform(0.3, 4.0, size=d)
    base = rng.normal(size=(n, d)) * scale
    # Strong correlation between axis 0 and 1.
    base[:, 1] = 0.85 * base[:, 0] + 0.15 * base[:, 1]
    return base + mean


def test_whitening_centers_and_unit_variance_on_own_corpus():
    x = _correlated_corpus(n=4000, d=12, seed=7)
    model = fit_whitening(x)
    whitened = whiten(x, model)
    axis_mean = whitened.mean(axis=0)
    axis_var = whitened.var(axis=0, ddof=1)
    assert axis_mean.shape == (12,)
    np.testing.assert_allclose(axis_mean, 0.0, atol=5e-2)
    np.testing.assert_allclose(axis_var, 1.0, atol=0.15)


def test_whitening_decorrelates_correlated_axes():
    x = _correlated_corpus(n=4000, d=8, seed=3)
    raw_corr = np.corrcoef(x[:, 0], x[:, 1])[0, 1]
    assert raw_corr > 0.7
    whitened = whiten(x, fit_whitening(x))
    whitened_corr = np.corrcoef(whitened[:, 0], whitened[:, 1])[0, 1]
    assert abs(whitened_corr) < 0.15


def test_single_vector_matches_matrix_row():
    x = _correlated_corpus(n=200, d=6, seed=1)
    model = fit_whitening(x)
    row = whiten(x[0], model)
    matrix = whiten(x, model)
    np.testing.assert_allclose(row, matrix[0], atol=1e-6)


def test_too_few_samples_raise():
    with pytest.raises(ValueError, match="at least"):
        fit_whitening(np.zeros((MIN_SAMPLES - 1, 4)))


def test_ridge_makes_singular_covariance_invertible():
    rng = np.random.default_rng(0)
    # Rank-1 cloud in 8D: empirical Sigma is singular without ridge.
    direction = rng.normal(size=8)
    x = rng.normal(size=(30, 1)) * direction
    model = fit_whitening(x, ridge_ratio=1e-3)
    assert model.ridge > 0.0
    whitened = whiten(x, model)
    assert np.isfinite(whitened).all()
    np.testing.assert_allclose(whitened.mean(axis=0), 0.0, atol=1e-6)


def test_roundtrip_npz(tmp_path: Path):
    x = _correlated_corpus(n=100, d=5, seed=2)
    model = fit_whitening(x)
    path = tmp_path / "whitening.npz"
    save_whitening(model, path)
    loaded = load_whitening(path)
    np.testing.assert_allclose(loaded.mu, model.mu)
    np.testing.assert_allclose(loaded.sigma_inv_sqrt, model.sigma_inv_sqrt)
    assert loaded.n_samples == model.n_samples
    assert loaded.dim == model.dim


def test_dense_matrix_from_knowledge_rows():
    rows = [
        {"vector": [1.0, 2.0, 3.0], "text": "a"},
        {"vector": [4.0, 5.0, 6.0], "text": "b"},
    ]
    matrix = dense_matrix_from_rows(rows)
    assert matrix.shape == (2, 3)
    np.testing.assert_array_equal(matrix[0], [1.0, 2.0, 3.0])


def test_automotive_demo_windows_cover_the_pack():
    body = load_demo_corpus_body("automotive_maintenance.pdf")
    windows = demo_sliding_windows(body)
    assert len(windows) >= 10
    assert any("Tire pressure" in w or "PSI" in w for w in windows)
    assert all(len(w) <= 512 for w in windows)


def test_sliding_windows_empty_text():
    assert sliding_windows("   ") == []


def test_whitening_model_is_frozen():
    model = fit_whitening(_correlated_corpus(80, 4, seed=4))
    assert isinstance(model, WhiteningModel)
    with pytest.raises(Exception):
        model.ridge = 0.0  # type: ignore[misc]
