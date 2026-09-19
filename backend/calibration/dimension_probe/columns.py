"""Per-column theme deltas. Lab. No embedder. No evaluate_clause.

The sheet is all D columns, extrema of every row (no mean).
Disjoint axes are the hard cut, not a ranked top-k.
"""

from __future__ import annotations

from itertools import combinations

import numpy as np

from calibration.dimension_probe.lomo import prisma_bucket_indices
from calibration.dimension_probe.metrics import envelope_bounds

THEME_KEYS: tuple[str, ...] = (
    "radio",
    "indice",
    "legal",
    "cubierta",
    "oficio",
    "piggy_clause_torta",
    "piggy_full",
    "names_chunk",
    "it_chunk",
    "poetry",
)

HEADLINE_LABELS: dict[tuple[str, str], str] = {
    ("radio", "piggy_clause_torta"): "radio vs torta",
    ("oficio", "piggy_clause_torta"): "oficio vs torta",
    ("radio", "oficio"): "radio vs oficio",
    ("indice", "piggy_clause_torta"): "indice vs torta",
}

_DISPLAY: dict[str, str] = {
    "piggy_clause_torta": "torta",
    "piggy_full": "piggy_full",
    "names_chunk": "nombres",
    "it_chunk": "IT",
    "poetry": "poesia",
}


def pair_label(left: str, right: str) -> str:
    key = (left, right) if (left, right) in HEADLINE_LABELS else (right, left)
    if key in HEADLINE_LABELS:
        return HEADLINE_LABELS[key]
    return f"{_DISPLAY.get(left, left)} vs {_DISPLAY.get(right, right)}"


def _round(v: float) -> float:
    return round(float(v), 5)


def _ceiling(delta_hi: float) -> str:
    if delta_hi > 1e-12:
        return "left"
    if delta_hi < -1e-12:
        return "right"
    return "tie"


def disjoint_indices(sheet: list[dict]) -> list[int]:
    """Every axis whose painted intervals do not overlap. Not a top-k."""
    return [int(r["dim"]) for r in sheet if not r["overlap"]]


def column_sheet(left: np.ndarray, right: np.ndarray) -> list[dict]:
    """One row per dimension. lo/hi of ALL left rows vs ALL right rows. No mean."""
    if left.ndim != 2 or right.ndim != 2:
        raise ValueError("left and right must be row-major matrices")
    if left.shape[1] != right.shape[1]:
        raise ValueError("dimension mismatch")
    lo_l, hi_l = envelope_bounds(left)
    lo_r, hi_r = envelope_bounds(right)
    overlap = (lo_l <= hi_r) & (lo_r <= hi_l)
    d_hi = hi_l - hi_r
    d_lo = lo_l - lo_r
    d_ext = np.maximum(np.abs(d_hi), np.abs(d_lo))
    gap = np.where(
        overlap,
        np.minimum(hi_l, hi_r) - np.maximum(lo_l, lo_r),
        np.maximum(lo_l, lo_r) - np.minimum(hi_l, hi_r),
    )
    rows: list[dict] = []
    for i in range(int(left.shape[1])):
        ov = bool(overlap[i])
        rows.append(
            {
                "dim": i,
                "lo_left": _round(lo_l[i]),
                "hi_left": _round(hi_l[i]),
                "lo_right": _round(lo_r[i]),
                "hi_right": _round(hi_r[i]),
                "delta_hi": _round(d_hi[i]),
                "delta_lo": _round(d_lo[i]),
                "delta_ext": _round(d_ext[i]),
                "overlap": ov,
                "gap": _round(gap[i]),
                "ceiling": _ceiling(float(d_hi[i])),
            }
        )
    return rows


def extrema_hist(sheet: list[dict]) -> dict:
    ext = np.asarray([r["delta_ext"] for r in sheet], dtype=np.float64)
    return {
        "dims": len(sheet),
        "dims_moved": int(np.sum(ext > 1e-12)),
        "dims_disjoint": int(sum(1 for r in sheet if not r["overlap"])),
        "min_delta_ext": _round(float(np.min(ext))),
        "median_delta_ext": _round(float(np.median(ext))),
        "max_delta_ext": _round(float(np.max(ext))),
        "n_gt": {
            "0.001": int(np.sum(ext > 0.001)),
            "0.01": int(np.sum(ext > 0.01)),
            "0.02": int(np.sum(ext > 0.02)),
            "0.05": int(np.sum(ext > 0.05)),
            "0.08": int(np.sum(ext > 0.08)),
            "0.10": int(np.sum(ext > 0.10)),
        },
    }


def column_pair(
    left: np.ndarray,
    right: np.ndarray,
    *,
    small_n_floor: int = 10,
) -> dict:
    if left.ndim != 2 or right.ndim != 2:
        raise ValueError("left and right must be row-major matrices")
    if left.shape[1] != right.shape[1]:
        raise ValueError("dimension mismatch")
    n_left = int(left.shape[0])
    n_right = int(right.shape[0])
    sheet = column_sheet(left, right)
    return {
        "n_left": n_left,
        "n_right": n_right,
        "small_n": n_left < small_n_floor or n_right < small_n_floor,
        "dims": int(left.shape[1]),
        "hist": extrema_hist(sheet),
        "disjoint": disjoint_indices(sheet),
        "sheet": sheet,
    }


def pair_matrix(
    groups: dict[str, np.ndarray],
    names: tuple[str, ...] = THEME_KEYS,
    *,
    small_n_floor: int = 10,
) -> dict:
    present = [n for n in names if n in groups and groups[n].shape[0] > 0]
    pairs: list[dict] = []
    for left, right in combinations(present, 2):
        body = column_pair(groups[left], groups[right], small_n_floor=small_n_floor)
        pairs.append(
            {
                "left": left,
                "right": right,
                "label": pair_label(left, right),
                **body,
            }
        )
    return {
        "families": {n: int(groups[n].shape[0]) for n in present},
        "n_pairs": len(pairs),
        "pairs": pairs,
    }


def slice_prisma_themes(prisma: np.ndarray, chunks: list[dict]) -> dict[str, np.ndarray]:
    """Slice prisma_chunk rows by classify_lomo primary reason."""
    n = int(prisma.shape[0])
    buckets = prisma_bucket_indices(chunks[:n])
    out: dict[str, np.ndarray] = {}
    for name, idxs in buckets.items():
        if not idxs:
            continue
        out[name] = prisma[np.asarray(idxs, dtype=np.intp)]
    return out


def theme_groups(
    groups: dict[str, np.ndarray],
    chunks: list[dict],
) -> dict[str, np.ndarray]:
    """Prisma slices + probe families listed in THEME_KEYS."""
    if "prisma_chunk" not in groups:
        raise RuntimeError("prisma_chunk missing — cannot slice themes.")
    out = slice_prisma_themes(groups["prisma_chunk"], chunks)
    for key in THEME_KEYS:
        if key in groups and key not in out:
            out[key] = groups[key]
    return {k: v for k, v in out.items() if k in THEME_KEYS and v.shape[0] > 0}
