"""Pure geometry for the dimension-probe lab. No embedder. No evaluate_clause."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def l2_normalize(rows: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(rows, axis=1, keepdims=True)
    norms = np.clip(norms, 1e-12, None)
    return rows / norms


def centroid(rows: np.ndarray) -> np.ndarray:
    return np.mean(rows, axis=0)


def cosine(a: np.ndarray, b: np.ndarray) -> float:
    an = a / max(float(np.linalg.norm(a)), 1e-12)
    bn = b / max(float(np.linalg.norm(b)), 1e-12)
    return float(np.dot(an, bn))


def pairwise_mean_cosine(left: np.ndarray, right: np.ndarray, cap: int = 80) -> float:
    """Mean cosine of up to cap×cap pairs. Deterministic: first cap rows."""
    a = l2_normalize(left[:cap])
    b = l2_normalize(right[:cap])
    gram = a @ b.T
    return float(np.mean(gram))


def intra_mean_cosine(rows: np.ndarray, cap: int = 80) -> float:
    a = l2_normalize(rows[:cap])
    gram = a @ a.T
    n = gram.shape[0]
    if n < 2:
        return 1.0
    tri = np.triu_indices(n, k=1)
    return float(np.mean(gram[tri]))


def dim_spans(rows: np.ndarray) -> np.ndarray:
    return np.max(rows, axis=0) - np.min(rows, axis=0)


def relative_slack(spans: np.ndarray, percent: float) -> np.ndarray:
    """Holgura relativa: slack = percent/100 * observed span per column."""
    return spans * (percent / 100.0)


def centroid_abs_delta(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    return np.abs(centroid(left) - centroid(right))


def top_moving_dims(delta: np.ndarray, k: int = 20) -> list[tuple[int, float]]:
    order = np.argsort(delta)[::-1]
    return [(int(i), float(delta[i])) for i in order[:k]]


def envelope_bounds(rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    return np.min(rows, axis=0), np.max(rows, axis=0)


def dim_inside_mask(row: np.ndarray, lo: np.ndarray, hi: np.ndarray, slack: np.ndarray) -> np.ndarray:
    return (row >= lo - slack) & (row <= hi + slack)


def fraction_dims_inside(
    rows: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    slack: np.ndarray,
) -> np.ndarray:
    masks = (rows >= lo - slack) & (rows <= hi + slack)
    return masks.mean(axis=1)


def rows_inside_strict(
    rows: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    slack: np.ndarray,
) -> float:
    frac = fraction_dims_inside(rows, lo, hi, slack)
    return float(np.mean(frac >= 1.0 - 1e-12))


def rows_inside_almost(
    rows: np.ndarray,
    lo: np.ndarray,
    hi: np.ndarray,
    slack: np.ndarray,
    dim_frac: float = 0.95,
) -> float:
    frac = fraction_dims_inside(rows, lo, hi, slack)
    return float(np.mean(frac >= dim_frac))


def mean_abs_zscore(rows: np.ndarray, mean: np.ndarray, std: np.ndarray) -> float:
    scale = np.clip(std, 1e-12, None)
    z = np.abs((rows - mean) / scale)
    return float(np.mean(z))


def span_compare(raw_rows: np.ndarray, oficio_rows: np.ndarray, k: int = 12) -> dict:
    """Per-axis tightening. Median span can stay flat while some columns shrink."""
    span_r = dim_spans(raw_rows)
    span_o = dim_spans(oficio_rows)
    delta = span_r - span_o
    order = np.argsort(delta)[::-1][:k]
    return {
        "dims": int(span_r.shape[0]),
        "dims_tighter": int(np.sum(delta > 1e-6)),
        "median_delta": round(float(np.median(delta)), 5),
        "p95_delta": round(float(np.quantile(delta, 0.95)), 5),
        "max_delta": round(float(np.max(delta)), 5),
        "top_shrink": [
            {
                "dim": int(i),
                "delta": round(float(delta[i]), 5),
                "span_raw": round(float(span_r[i]), 5),
                "span_oficio": round(float(span_o[i]), 5),
            }
            for i in order
        ],
    }


def same_sign_dim_count(rows: np.ndarray) -> int:
    """vhectorlab shared-noise veto: dims where min and max share sign (0 counts +)."""
    lo = np.min(rows, axis=0)
    hi = np.max(rows, axis=0)
    lo_sign = np.where(lo >= 0.0, 1, -1)
    hi_sign = np.where(hi >= 0.0, 1, -1)
    return int(np.sum(lo_sign == hi_sign))


@dataclass(frozen=True)
class GroupPair:
    name: str
    centroid_cosine: float
    pairwise_cosine: float
    median_abs_delta: float
    top_dims: list[tuple[int, float]]
