"""Integration calibration tests for Manual Gol 2020.pdf (hand-curated Spanish dataset)."""
from __future__ import annotations

import pytest

from app.core.recommended_thresholds import build_data_driven_grids
from app.modules.corpus_calibration import (
    calibrate_positive_for_pack,
    resolve_dataset_for_pack,
)
from app.modules.storage import storage

GOL_FILENAME = "Manual Gol 2020.pdf"
GOL_DATASET = "gol_2020_v1.json"


def _gol_pack_loaded() -> bool:
    return any(p["filename"] == GOL_FILENAME for p in storage.get_summary())


@pytest.mark.integration
@pytest.mark.skipif(not _gol_pack_loaded(), reason=f"{GOL_FILENAME} not loaded in LanceDB")
def test_gol_hand_curated_dataset_resolves():
    dataset = resolve_dataset_for_pack(GOL_FILENAME)
    assert dataset is not None
    assert dataset["corpus_file"] == GOL_FILENAME
    from pathlib import Path
    assert Path(dataset["_path"]).name == GOL_DATASET
    assert len(dataset["queries"]) == 25
    on_corpus = [q for q in dataset["queries"] if q["category"] == "on_corpus"]
    assert len(on_corpus) == 9
    assert all("¿" in q["text"] or "?" in q["text"] for q in on_corpus)


@pytest.mark.integration
@pytest.mark.skipif(not _gol_pack_loaded(), reason=f"{GOL_FILENAME} not loaded in LanceDB")
def test_gol_calibration_meets_accuracy_and_uses_conservative_tiebreak():
    """Full embed + 2D sweep against production LanceDB for the Gol pack."""
    result = calibrate_positive_for_pack(GOL_FILENAME)
    assert result.dataset_file == GOL_DATASET
    assert result.accuracy >= 0.92
    assert result.sweep_summary["thresholds_2d"]["noise_swept"] is False
    assert result.sweep_summary["thresholds_2d"]["youden"] >= 0.85
    assert 0.35 <= result.cosine_threshold <= 0.75
    assert 0 <= result.excitation_threshold <= 300
    # Conservative tie-break: excitation should not sit at grid floor when higher values also win.
    assert result.excitation_threshold >= 50 or result.sweep_summary["thresholds_2d"]["f1"] < 1.0


@pytest.mark.integration
@pytest.mark.skipif(not _gol_pack_loaded(), reason=f"{GOL_FILENAME} not loaded in LanceDB")
def test_gol_data_driven_grid_spans_separation_zone():
    from app.modules.corpus_calibration import (
        _calibration_base_cfg,
        _measure_calibration_dataset,
    )

    dataset = resolve_dataset_for_pack(GOL_FILENAME)
    cfg = _calibration_base_cfg()
    rows = _measure_calibration_dataset(dataset, GOL_FILENAME, cfg)
    grids = build_data_driven_grids(rows)
    cos = grids["cosine_threshold"]
    exc = grids["excitation_threshold"]
    assert len(cos) >= 10
    assert len(exc) >= 10
    assert min(cos) <= 0.55
    assert max(cos) >= 0.55
    assert min(exc) <= 150
    assert max(exc) >= 100
