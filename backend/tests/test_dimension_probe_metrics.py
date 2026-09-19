"""Dimension-probe metrics: fake rows only. Does not load BGE-M3."""

from __future__ import annotations

import numpy as np

from calibration.dimension_probe.metrics import (
    centroid,
    centroid_abs_delta,
    cosine,
    dim_spans,
    intra_mean_cosine,
    pairwise_mean_cosine,
    relative_slack,
    same_sign_dim_count,
    top_moving_dims,
)


def test_cosine_identical_rows_is_one() -> None:
    v = np.array([1.0, 2.0, 3.0])
    assert cosine(v, v) == 1.0


def test_mechanic_it_closer_than_names_on_fake_axes() -> None:
    # dim0 = technical, dim1 = names
    mechanic = np.array([[1.0, 0.0], [0.9, 0.05], [1.1, 0.02]])
    it = np.array([[0.95, 0.01], [1.05, 0.0], [1.0, 0.04]])
    names = np.array([[0.0, 1.0], [0.05, 0.9], [0.02, 1.1]])
    tech = cosine(centroid(mechanic), centroid(it))
    vs_names = cosine(centroid(mechanic), centroid(names))
    assert tech > vs_names


def test_span_compare_sees_the_axis_median_hides() -> None:
    from calibration.dimension_probe.metrics import span_compare

    oficio = np.array([[0.0, 0.0, 0.0], [1.0, 0.02, 0.5]], dtype=np.float32)
    raw = np.vstack([oficio, np.array([[0.5, 0.039, 0.5]], dtype=np.float32)])
    cmp = span_compare(raw, oficio, k=2)
    assert cmp["dims_tighter"] == 1
    assert cmp["median_delta"] == 0.0
    assert cmp["top_shrink"][0]["dim"] == 1
    assert cmp["top_shrink"][0]["delta"] > 0.0


def test_holgura_relativa_is_percent_of_span() -> None:
    rows = np.array([[0.0, 10.0], [2.0, 12.0]])
    spans = dim_spans(rows)
    slack = relative_slack(spans, 10.0)
    assert np.allclose(spans, [2.0, 2.0])
    assert np.allclose(slack, [0.2, 0.2])


def test_top_moving_dims_ranks_the_wide_axis() -> None:
    left = np.array([[0.0, 0.0], [0.0, 0.0]])
    right = np.array([[5.0, 0.1], [5.0, 0.1]])
    delta = centroid_abs_delta(left, right)
    top = top_moving_dims(delta, k=1)
    assert top[0][0] == 0
    assert top[0][1] == 5.0


def test_same_sign_counts_only_unipolar_columns() -> None:
    rows = np.array([[1.0, -2.0], [3.0, 4.0]])
    assert same_sign_dim_count(rows) == 1


def test_pairwise_and_intra_stay_bounded() -> None:
    rng = np.random.default_rng(0)
    a = rng.normal(size=(12, 8))
    b = rng.normal(size=(12, 8))
    pair = pairwise_mean_cosine(a, b, cap=8)
    intra = intra_mean_cosine(a, cap=8)
    assert -1.0 <= pair <= 1.0
    assert -1.0 <= intra <= 1.0
