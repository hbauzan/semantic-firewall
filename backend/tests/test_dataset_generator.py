"""Tests for auto-generated calibration datasets."""
import pytest
from unittest.mock import patch

from app.modules.dataset_generator import (
    TOTAL_QUERIES,
    _build_queries,
    _generate_on_corpus_template,
    _is_verbatim_leakage,
    filename_to_slug,
    generate_dataset_for_pack,
)


def test_filename_to_slug_prisma_like():
    slug = filename_to_slug("om_ng-chevrolet_Prisma_my15-es_AR.pdf.pdf")
    assert slug == "om_ng_chevrolet_prisma_my15_es_ar"


def test_generate_dataset_schema(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "app.modules.dataset_generator.DATASETS_DIR",
        tmp_path,
    )
    fingerprint = {"filename": "test_pack.pdf", "chunk_count": 3, "text_hash": "abc123"}

    with (
        patch("app.modules.dataset_generator.storage.get_pack_fingerprint", return_value=fingerprint),
        patch("app.modules.dataset_generator.storage.get_pack_text_sample", return_value="Engine maintenance guide for diesel trucks."),
        patch("app.modules.dataset_generator.storage._pack_rows", return_value=[
            {"text": "Chapter 1: Diesel engine oil change intervals."},
            {"text": "Torque specifications for cylinder head bolts."},
        ]),
        patch("app.modules.dataset_generator.complete_prompt", return_value=None),
        patch("app.modules.dataset_generator._is_verbatim_leakage", return_value=False),
    ):
        dataset = generate_dataset_for_pack("test_pack.pdf")

    assert dataset["schema_version"] == "1.0"
    assert dataset["corpus_file"] == "test_pack.pdf"
    assert dataset["generation_method"] == "template_fallback"
    assert len(dataset["queries"]) == TOTAL_QUERIES

    categories = {q["category"] for q in dataset["queries"]}
    assert categories == {"on_corpus", "off_topic", "piggybacking", "adversarial"}

    on_corpus = [q for q in dataset["queries"] if q["category"] == "on_corpus"]
    assert len(on_corpus) == 9
    assert all(q["expected"] == "pass" for q in on_corpus)


def test_no_verbatim_leakage():
    chunks = [
        "The recommended cold tire pressure for rear axle is 32 PSI.",
        "Brake pads should be inspected every 12000 miles.",
    ]
    with patch("app.modules.dataset_generator._cosine_sim", return_value=0.5):
        assert _is_verbatim_leakage(
            "The recommended cold tire pressure for rear axle is 32 PSI?",
            chunks,
        )
        assert not _is_verbatim_leakage(
            "What tire pressure is suggested for the rear wheels?",
            chunks,
        )


def test_build_queries_count():
    on = _generate_on_corpus_template("diesel engines")
    off = ["Off topic question one?", "Off topic question two?"] * 4
    adv = ["Adversarial jailbreak one.", "Adversarial jailbreak two."] * 2
    queries = _build_queries(on, off, adv, "diesel")
    assert len(queries) == TOTAL_QUERIES


def test_calibrate_any_loaded_pack(monkeypatch):
    from app.modules.corpus_calibration import (
        TripleSweepPoint,
        calibrate_positive_for_pack,
    )

    generated = {
        "_path": "/fake/auto_test.json",
        "corpus_id": "test",
        "corpus_file": "random_manual.pdf",
        "generation_method": "template_fallback",
        "queries": [{"id": "q1", "text": "What about diesel?", "expected": "pass"}],
    }
    winner = TripleSweepPoint(0.48, 100, 4.5, tp=18, fp=2, tn=4, fn=1)

    with (
        patch("app.modules.corpus_calibration.storage.get_summary", return_value=[{"filename": "random_manual.pdf"}]),
        patch("app.modules.corpus_calibration.resolve_dataset_for_pack", return_value=None),
        patch("app.modules.dataset_generator.generate_dataset_for_pack", return_value=generated),
        patch("app.modules.corpus_calibration._measure_calibration_dataset", return_value=[]),
        patch(
            "app.modules.corpus_calibration._sweep_thresholds_3d",
            return_value=[winner],
        ),
        patch(
            "app.modules.corpus_calibration._run_evaluation",
            return_value=[("q1", "pass", "pass", True)],
        ),
    ):
        result = calibrate_positive_for_pack("random_manual.pdf")

    assert result.generation_method == "template_fallback"
    assert result.cosine_threshold == 0.48


def test_calibrate_task_progress():
    from app.modules.corpus_calibration import (
        TripleSweepPoint,
        calibrate_positive_for_pack,
    )

    progress_log: list[float] = []

    def progress_cb(progress: float, _message: str) -> None:
        progress_log.append(progress)

    dataset = {
        "_path": "/fake/auto.json",
        "corpus_id": "x",
        "corpus_file": "pack.pdf",
        "queries": [{"id": "q1", "text": "t", "expected": "pass"}],
    }

    def fake_3d(*_args, progress_cb=None, **_kwargs):
        if progress_cb:
            progress_cb(40.0, "3D sweep… (1/1287)")
        return [TripleSweepPoint(0.5, 150, 4.5, tp=1, fp=0, tn=0, fn=0)]

    with (
        patch("app.modules.corpus_calibration.storage.get_summary", return_value=[{"filename": "pack.pdf"}]),
        patch("app.modules.corpus_calibration.resolve_dataset_for_pack", return_value=dataset),
        patch("app.modules.corpus_calibration._measure_calibration_dataset", return_value=[]),
        patch("app.modules.corpus_calibration._sweep_thresholds_3d", side_effect=fake_3d),
        patch(
            "app.modules.corpus_calibration._run_evaluation",
            return_value=[("q1", "pass", "pass", True)],
        ),
    ):
        calibrate_positive_for_pack("pack.pdf", progress_cb=progress_cb)

    assert progress_log == sorted(progress_log)
    assert progress_log[-1] >= 95.0
