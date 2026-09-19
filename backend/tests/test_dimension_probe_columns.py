"""Column-wise theme deltas. Fake rows only. Does not load BGE-M3."""

from __future__ import annotations

import numpy as np

from calibration.dimension_probe.columns import (
    THEME_KEYS,
    column_pair,
    pair_matrix,
    slice_prisma_themes,
)
from calibration.dimension_probe.lomo import prisma_bucket_indices


_INDEX = (
    "Iluminación exterior. . . . . . . . . . . . 6-1 "
    "Sistema de infoentretenimiento . . . . . . . . . 7-1 "
    "Radio . . . . . . . . . . . . . . . . . . . . . . . . . 7-9 "
    "Índice . . . . . . . . . . . . . . . . . . . . i-1"
)
_RADIO = (
    "Sistema de infoentretenimiento 7-9 "
    "Radio AM-FM. Pulse [telephone] en el menú de inicio. "
    "Si el teléfono Bluetooth no estuviera conectado al sistema de infoentretenimiento."
)
_OIL = (
    "Compruebe el nivel de aceite del motor antes de recurrir a la asistencia "
    "de un concesionario. Consulte Aceite del motor en la página 10-11."
)


def _radio_torta_oficio() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    # dim1: radio ceiling 0.039, torta 0.027, oficio 0.012
    radio = np.array([[0.0, 0.039, 0.01], [0.01, 0.035, 0.01]], dtype=np.float32)
    torta = np.array([[0.0, 0.027, 0.01], [0.01, 0.025, 0.01]], dtype=np.float32)
    oficio = np.array([[0.0, 0.010, 0.01], [0.01, 0.012, 0.01]], dtype=np.float32)
    return radio, torta, oficio


def test_sheet_has_every_dimension_no_mean() -> None:
    radio, torta, _oficio = _radio_torta_oficio()
    pair = column_pair(radio, torta)
    assert pair["dims"] == 3
    assert len(pair["sheet"]) == 3
    assert {r["dim"] for r in pair["sheet"]} == {0, 1, 2}
    assert all("mean_left" not in r for r in pair["sheet"])
    assert pair["hist"]["dims"] == 3
    assert pair["hist"]["dims_moved"] == 1
    assert pair["sheet"][1]["dim"] == 1


def test_column_pair_has_no_mean_ranking() -> None:
    radio, torta, _oficio = _radio_torta_oficio()
    pair = column_pair(radio, torta)
    assert pair["n_left"] == 2
    assert pair["n_right"] == 2
    assert "top_mean" not in pair
    assert "top_hi" not in pair
    assert "median_delta_mean" not in pair
    assert "max_delta_mean" not in pair
    assert pair["disjoint"] == [1]
    assert pair["sheet"][1]["hi_left"] > pair["sheet"][1]["hi_right"]


def test_pair_matrix_covers_every_theme_pair() -> None:
    radio, torta, oficio = _radio_torta_oficio()
    groups = {
        "radio": radio,
        "piggy_clause_torta": torta,
        "oficio": oficio,
    }
    names = ("radio", "piggy_clause_torta", "oficio")
    mat = pair_matrix(groups, names, small_n_floor=1)
    assert len(mat["pairs"]) == 3
    labels = {p["label"] for p in mat["pairs"]}
    assert "radio vs torta" in labels
    assert "oficio vs torta" in labels
    assert "radio vs oficio" in labels
    radio_torta = next(p for p in mat["pairs"] if p["label"] == "radio vs torta")
    assert radio_torta["small_n"] is False
    assert radio_torta["disjoint"] == [1]


def test_small_n_is_declared() -> None:
    left = np.array([[0.0, 1.0]], dtype=np.float32)
    right = np.ones((12, 2), dtype=np.float32)
    pair = column_pair(left, right, small_n_floor=10)
    assert pair["small_n"] is True


def test_theme_keys_match_the_plan() -> None:
    assert "radio" in THEME_KEYS
    assert "piggy_clause_torta" in THEME_KEYS
    assert "oficio" in THEME_KEYS
    assert "cubierta" in THEME_KEYS


def test_prisma_buckets_split_radio_from_oficio() -> None:
    chunks = [
        {"index": 0, "text": _RADIO},
        {"index": 1, "text": _OIL},
        {"index": 2, "text": _INDEX},
    ]
    buckets = prisma_bucket_indices(chunks)
    assert buckets["radio"] == (0,)
    assert buckets["oficio"] == (1,)
    assert buckets["indice"] == (2,)
    prisma = np.array(
        [[0.0, 0.039], [0.0, 0.010], [0.0, 0.020]],
        dtype=np.float32,
    )
    themes = slice_prisma_themes(prisma, chunks)
    assert themes["radio"].shape == (1, 2)
    assert np.isclose(float(themes["radio"][0, 1]), 0.039)
    assert themes["oficio"].shape == (1, 2)
