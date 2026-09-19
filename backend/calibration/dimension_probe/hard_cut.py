"""Hard cut on a painted lock. Lab. No embedder. No evaluate_clause.

Every axis votes (left_only / right_only / both / neither).
The hard label uses only the disjoint axes. The other axes are not dropped.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from calibration.dimension_probe.columns import column_sheet, disjoint_indices, pair_label
from calibration.dimension_probe.metrics import envelope_bounds

LEFT_ONLY = 0
RIGHT_ONLY = 1
BOTH = 2
NEITHER = 3

_VOTE_NAME = {
    LEFT_ONLY: "left_only",
    RIGHT_ONLY: "right_only",
    BOTH: "both",
    NEITHER: "neither",
}

_LABELS = ("left", "right", "split", "out")


def vote_codes(
    rows: np.ndarray,
    lo_l: np.ndarray,
    hi_l: np.ndarray,
    lo_r: np.ndarray,
    hi_r: np.ndarray,
) -> np.ndarray:
    """(n, D) uint8. Closed intervals. Every column votes."""
    if rows.ndim != 2:
        raise ValueError("rows must be row-major")
    in_l = (rows >= lo_l) & (rows <= hi_l)
    in_r = (rows >= lo_r) & (rows <= hi_r)
    codes = np.full(rows.shape, NEITHER, dtype=np.uint8)
    codes[in_l & ~in_r] = LEFT_ONLY
    codes[~in_l & in_r] = RIGHT_ONLY
    codes[in_l & in_r] = BOTH
    return codes


def hard_cut_label(codes_row, disjoint: list[int] | tuple[int, ...]) -> str:
    """left / right / split / out. Empty disjoint → out (no hard axis)."""
    if not disjoint:
        return "out"
    votes = [int(codes_row[i]) for i in disjoint]
    if any(v == NEITHER or v == BOTH for v in votes):
        return "out"
    lefts = all(v == LEFT_ONLY for v in votes)
    rights = all(v == RIGHT_ONLY for v in votes)
    if lefts:
        return "left"
    if rights:
        return "right"
    return "split"


def _tally(row: np.ndarray) -> dict[str, int]:
    return {
        "n_left_only": int(np.sum(row == LEFT_ONLY)),
        "n_right_only": int(np.sum(row == RIGHT_ONLY)),
        "n_both": int(np.sum(row == BOTH)),
        "n_neither": int(np.sum(row == NEITHER)),
    }


def press_rows(
    rows: np.ndarray,
    lo_l: np.ndarray,
    hi_l: np.ndarray,
    lo_r: np.ndarray,
    hi_r: np.ndarray,
    disjoint: list[int] | tuple[int, ...],
) -> list[dict]:
    """One record per row. No mean. Tallies sum to D."""
    codes = vote_codes(rows, lo_l, hi_l, lo_r, hi_r)
    d = int(rows.shape[1])
    out: list[dict] = []
    for i, row in enumerate(codes):
        t = _tally(row)
        if t["n_left_only"] + t["n_right_only"] + t["n_both"] + t["n_neither"] != d:
            raise RuntimeError("vote tally does not cover every dimension")
        out.append(
            {
                "i": i,
                **t,
                "inside_left": t["n_left_only"] + t["n_both"] == d,
                "inside_right": t["n_right_only"] + t["n_both"] == d,
                "hard_cut": hard_cut_label(row, disjoint),
                "disjoint_votes": [
                    {"dim": int(j), "vote": _VOTE_NAME[int(row[j])]} for j in disjoint
                ],
            }
        )
    return out


def _census(records: list[dict]) -> dict[str, int]:
    counts = {k: 0 for k in _LABELS}
    for r in records:
        counts[r["hard_cut"]] += 1
    return counts


def _tally_extrema(records: list[dict]) -> dict[str, dict[str, int]]:
    keys = ("n_left_only", "n_right_only", "n_both", "n_neither")
    if not records:
        return {k: {"lo": 0, "hi": 0} for k in keys}
    return {
        k: {
            "lo": min(r[k] for r in records),
            "hi": max(r[k] for r in records),
        }
        for k in keys
    }


def press_lock(
    groups: dict[str, np.ndarray],
    *,
    left_key: str,
    right_key: str,
) -> dict:
    """Paint [lo,hi] from left and right mazos. Press every group, every row."""
    if left_key not in groups or right_key not in groups:
        raise KeyError(f"lock needs {left_key!r} and {right_key!r}")
    left, right = groups[left_key], groups[right_key]
    if left.ndim != 2 or right.ndim != 2 or left.shape[1] != right.shape[1]:
        raise ValueError("lock matrices must share D")
    lo_l, hi_l = envelope_bounds(left)
    lo_r, hi_r = envelope_bounds(right)
    sheet = column_sheet(left, right)
    disjoint = disjoint_indices(sheet)
    families: dict[str, dict] = {}
    votes: dict[str, np.ndarray] = {}
    for name, mat in groups.items():
        if mat.ndim != 2 or mat.shape[1] != left.shape[1] or mat.shape[0] == 0:
            continue
        records = press_rows(mat, lo_l, hi_l, lo_r, hi_r, disjoint)
        families[name] = {
            "n": int(mat.shape[0]),
            "census": _census(records),
            "tally_extrema": _tally_extrema(records),
            "rows": records,
        }
        votes[name] = vote_codes(mat, lo_l, hi_l, lo_r, hi_r)
    return {
        "left": left_key,
        "right": right_key,
        "label": pair_label(left_key, right_key),
        "n_left": int(left.shape[0]),
        "n_right": int(right.shape[0]),
        "dims": int(left.shape[1]),
        "disjoint": disjoint,
        "families": families,
        "_votes": votes,
    }


def _out_dir() -> Path:
    return Path(__file__).resolve().parent / "out"


def _public_lock(lock: dict) -> dict:
    return {k: v for k, v in lock.items() if k != "_votes"}


def _rows_csv(lock: dict, left_key: str, right_key: str) -> str:
    disjoint = lock["disjoint"]
    headers = [
        "family",
        "i",
        "hard_cut",
        "inside_left",
        "inside_right",
        "n_left_only",
        "n_right_only",
        "n_both",
        "n_neither",
    ]
    headers.extend(f"d{j}" for j in disjoint)
    lines = [",".join(headers)]
    for key in (left_key, right_key):
        fam = lock["families"].get(key)
        if fam is None:
            continue
        for r in fam["rows"]:
            votes = {v["dim"]: v["vote"] for v in r["disjoint_votes"]}
            cells = [
                key,
                str(r["i"]),
                r["hard_cut"],
                str(r["inside_left"]).lower(),
                str(r["inside_right"]).lower(),
                str(r["n_left_only"]),
                str(r["n_right_only"]),
                str(r["n_both"]),
                str(r["n_neither"]),
            ]
            cells.extend(votes[j] for j in disjoint)
            lines.append(",".join(cells))
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Press every row on a painted lock (no embed).")
    parser.add_argument("--rows", type=Path, default=None)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    out = args.out or _out_dir()
    rows_path = args.rows or (out / "rows.npz")
    if not rows_path.is_file():
        raise SystemExit(f"missing {rows_path} — run the probe once, then this.")
    blob = np.load(rows_path)
    groups = {k: blob[k] for k in blob.files}

    locks = []
    vote_arrays: dict[str, np.ndarray] = {}
    specs = (
        ("radio", "piggy_clause_torta"),
        ("oficio", "piggy_clause_torta"),
    )
    for left_key, right_key in specs:
        if left_key not in groups or right_key not in groups:
            continue
        lock = press_lock(groups, left_key=left_key, right_key=right_key)
        tag = f"{left_key}__{right_key}"
        for name, mat in lock["_votes"].items():
            vote_arrays[f"{tag}/{name}"] = mat
        locks.append(_public_lock(lock))
        if left_key == "radio":
            (out / "hard_cut_radio_torta_rows.csv").write_text(
                _rows_csv(lock, left_key, right_key),
                encoding="utf-8",
            )

    payload = {"locks": locks, "source": str(rows_path)}
    (out / "hard_cut.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if vote_arrays:
        np.savez_compressed(out / "hard_cut_votes.npz", **vote_arrays)
    print(
        json.dumps(
            {
                "source": str(rows_path),
                "locks": [
                    {
                        "label": lk["label"],
                        "disjoint": lk["disjoint"],
                        "census": {n: f["census"] for n, f in lk["families"].items()},
                    }
                    for lk in locks
                ],
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
