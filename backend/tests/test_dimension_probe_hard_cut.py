"""Hard cut: every axis votes. Disjoint axes decide. Fake rows only."""

from __future__ import annotations

import numpy as np

from calibration.dimension_probe.columns import column_sheet, disjoint_indices
from calibration.dimension_probe.hard_cut import (
    BOTH,
    LEFT_ONLY,
    NEITHER,
    RIGHT_ONLY,
    hard_cut_label,
    press_lock,
    press_rows,
    vote_codes,
)


def _mazos() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # dim0 overlap, dim1 disjoint, dim2 overlap
    left = np.array(
        [
            [0.0, 0.50, 0.00],
            [1.0, 1.00, 0.20],
        ],
        dtype=np.float32,
    )
    right = np.array(
        [
            [0.5, -1.00, 0.10],
            [1.5, 0.00, 0.30],
        ],
        dtype=np.float32,
    )
    other = np.array(
        [
            [0.0, -0.50, 0.15],  # split on dim1
            [0.0, 0.25, 0.00],  # dim1 in the gap
        ],
        dtype=np.float32,
    )
    return left, right, other


def test_disjoint_indices_are_every_non_overlapping_axis() -> None:
    left, right, _other = _mazos()
    sheet = column_sheet(left, right)
    assert disjoint_indices(sheet) == [1]


def test_vote_codes_cover_every_dimension() -> None:
    left, right, _other = _mazos()
    lo_l, hi_l = left.min(0), left.max(0)
    lo_r, hi_r = right.min(0), right.max(0)
    codes = vote_codes(left, lo_l, hi_l, lo_r, hi_r)
    assert codes.shape == (2, 3)
    assert list(codes[0]) == [LEFT_ONLY, LEFT_ONLY, LEFT_ONLY]
    assert list(codes[1]) == [BOTH, LEFT_ONLY, BOTH]


def test_hard_cut_uses_disjoint_axes_only() -> None:
    assert hard_cut_label([LEFT_ONLY, LEFT_ONLY, BOTH], [1]) == "left"
    assert hard_cut_label([BOTH, RIGHT_ONLY, BOTH], [1]) == "right"
    # one disjoint axis cannot split; conflict needs two hard axes
    assert hard_cut_label([LEFT_ONLY, RIGHT_ONLY, BOTH], [1]) == "right"
    assert hard_cut_label([LEFT_ONLY, RIGHT_ONLY, BOTH], [0, 1]) == "split"
    assert hard_cut_label([LEFT_ONLY, NEITHER, LEFT_ONLY], [1]) == "out"


def test_press_rows_is_one_record_per_row_no_mean() -> None:
    left, right, other = _mazos()
    lo_l, hi_l = left.min(0), left.max(0)
    lo_r, hi_r = right.min(0), right.max(0)
    rows = press_rows(other, lo_l, hi_l, lo_r, hi_r, disjoint=(1,))
    assert len(rows) == 2
    assert all("mean" not in "".join(k for k in r) for r in rows)
    assert rows[0]["n_left_only"] + rows[0]["n_right_only"] + rows[0]["n_both"] + rows[0][
        "n_neither"
    ] == 3
    assert rows[0]["hard_cut"] == "right"
    assert rows[1]["hard_cut"] == "out"
    assert rows[0]["disjoint_votes"] == [{"dim": 1, "vote": "right_only"}]
    assert rows[1]["disjoint_votes"] == [{"dim": 1, "vote": "neither"}]


def test_press_lock_paints_from_both_mazos_and_presses_every_group() -> None:
    left, right, other = _mazos()
    out = press_lock(
        {
            "radio": left,
            "piggy_clause_torta": right,
            "oficio": other,
        },
        left_key="radio",
        right_key="piggy_clause_torta",
    )
    assert out["dims"] == 3
    assert out["disjoint"] == [1]
    assert set(out["families"]) == {"radio", "piggy_clause_torta", "oficio"}
    radio = out["families"]["radio"]
    assert radio["n"] == 2
    assert len(radio["rows"]) == 2
    assert radio["census"] == {"left": 2, "right": 0, "split": 0, "out": 0}
    assert all(r["inside_left"] for r in radio["rows"])
    assert not any(r["inside_right"] for r in radio["rows"])
    torta = out["families"]["piggy_clause_torta"]
    assert torta["census"] == {"left": 0, "right": 2, "split": 0, "out": 0}
    oficio = out["families"]["oficio"]
    assert oficio["census"] == {"left": 0, "right": 1, "split": 0, "out": 1}
    keys = {k for fam in out["families"].values() for r in fam["rows"] for k in r}
    assert not any("mean" in k for k in keys)


def test_no_disjoint_axis_means_everyone_out() -> None:
    left = np.zeros((2, 3), dtype=np.float32)
    right = np.zeros((2, 3), dtype=np.float32)
    right[1, 0] = 0.1
    out = press_lock({"radio": left, "piggy_clause_torta": right}, left_key="radio", right_key="piggy_clause_torta")
    assert out["disjoint"] == []
    assert out["families"]["radio"]["census"] == {"left": 0, "right": 0, "split": 0, "out": 2}
