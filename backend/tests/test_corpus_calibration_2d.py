"""Tests for 2D cosine×excitation calibration sweep."""
from unittest.mock import patch

from app.core.models import ConfigState
from app.core.recommended_thresholds import (
    POSITIVE_RECOMMENDED,
    SWEEP_GRIDS,
    cosine_excitation_2d_grid_size,
)
from app.modules.corpus_calibration import (
    JointSweepPoint,
    SweepPoint,
    _pick_joint_youden_winner,
    _sweep_cosine_excitation_2d,
    calibrate_positive_for_pack,
)


def test_cosine_excitation_2d_grid_size():
    n_cos, n_exc = cosine_excitation_2d_grid_size()
    assert n_cos == len(SWEEP_GRIDS["cosine_threshold"])
    assert n_exc == len(SWEEP_GRIDS["excitation_threshold"])
    assert n_cos * n_exc >= 50


def test_joint_youden_winner_prefers_higher_recall_minus_fpr():
    low = JointSweepPoint(0.3, 25, tp=10, fp=5, tn=5, fn=5)
    high = JointSweepPoint(0.5, 150, tp=12, fp=3, tn=7, fn=3)
    assert _pick_joint_youden_winner([low, high]) == high


def test_2d_sweep_fixes_noise_at_recommended():
    dataset = {"queries": []}
    base_cfg = ConfigState(firewall_mode="positive")
    noise_fixed = POSITIVE_RECOMMENDED["global_noise_limit"]
    seen_noise: list[float] = []

    def fake_eval(_dataset, cfg, _pack):
        seen_noise.append(cfg.global_noise_limit)
        return [("q1", "pass", "pass", True)]

    with patch("app.modules.corpus_calibration._run_evaluation", side_effect=fake_eval):
        points = _sweep_cosine_excitation_2d(base_cfg, dataset, "pack.pdf", noise_fixed)

    assert len(points) == cosine_excitation_2d_grid_size()[0] * cosine_excitation_2d_grid_size()[1]
    assert all(n == noise_fixed for n in seen_noise)


def test_calibrate_positive_orchestrates_2d_then_noise():
    dataset = {
        "_path": "/fake/automotive_v1.json",
        "corpus_id": "automotive",
        "corpus_file": "automotive_maintenance.pdf",
        "queries": [{"id": "q1", "text": "x", "expected": "pass"}],
    }
    joint_winner = JointSweepPoint(0.48, 100, tp=18, fp=2, tn=4, fn=1)
    joint_runner = JointSweepPoint(0.33, 25, tp=10, fp=5, tn=1, fn=9)
    noise_winner = SweepPoint("global_noise_limit", 4.5, tp=20, fp=1, tn=4, fn=0)

    with (
        patch("app.modules.corpus_calibration.storage.get_summary", return_value=[{"filename": "automotive_maintenance.pdf"}]),
        patch("app.modules.corpus_calibration.resolve_dataset_for_pack", return_value=dataset),
        patch(
            "app.modules.corpus_calibration._sweep_cosine_excitation_2d",
            return_value=[joint_runner, joint_winner],
        ),
        patch(
            "app.modules.corpus_calibration._sweep_1d",
            return_value=[noise_winner],
        ),
        patch(
            "app.modules.corpus_calibration._run_evaluation",
            return_value=[("q1", "pass", "pass", True)],
        ),
    ):
        result = calibrate_positive_for_pack("automotive_maintenance.pdf")

    assert result.cosine_threshold == 0.48
    assert result.excitation_threshold == 100
    assert result.global_noise_limit == 4.5
    assert result.sweep_summary["cosine_excitation_2d"]["grid_pairs"] == 2
    assert result.sweep_summary["global_noise_limit_1d"]["optimal"] == 4.5
