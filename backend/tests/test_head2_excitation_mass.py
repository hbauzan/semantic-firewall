"""Head 2 — coarse excitation mass.

N_act counts coordinates whose unrounded |Q_d - C_d| stays inside ε_coarse.
A two-dimension spike can keep cos above tau_cos and still fail this gate.
"""
from __future__ import annotations

import math

import numpy as np
import pytest

from app.core.firewall import SemanticFirewall
from app.core.models import ConfigState

DIM = 1024
EPSILON = 0.015


def _pair_with_deltas(deltas: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    corpus = np.zeros(DIM, dtype=np.float32)
    query = np.asarray(deltas, dtype=np.float32)
    return query, corpus


def test_broad_mass_passes_when_three_hundred_coordinates_agree():
    deltas = np.full(DIM, 0.02, dtype=np.float32)
    deltas[:300] = 0.0
    query, corpus = _pair_with_deltas(deltas)
    cfg = ConfigState(noise_tolerance=EPSILON, excitation_threshold=150)
    passed, stage, details = SemanticFirewall.run_excitation_filter(
        query, corpus, cfg, word_count=10
    )
    assert stage == "excitation"
    assert details["activations"] == 300
    assert 0 <= details["activations"] <= DIM
    assert details["activations"] >= cfg.excitation_threshold
    assert passed is True


def test_spike_passes_head1_and_breaches_head2():
    """Two shared spikes hold cos near 0.85. The other 1022 axes sit outside ε."""
    gap = np.float32(0.02)
    assert float(gap) > EPSILON
    tail = 1022
    # s^2 = 0.7225 * tail * d^2 / 0.555  so the float64 cosine is 0.85
    spike = math.sqrt(0.7225 * tail * float(gap) ** 2 / 0.555)
    query = np.full(DIM, gap, dtype=np.float64)
    corpus = np.zeros(DIM, dtype=np.float64)
    query[:2] = spike
    corpus[:2] = spike

    cfg = ConfigState(
        cosine_threshold=0.5315,
        noise_tolerance=EPSILON,
        excitation_threshold=150,
        cosine_order=1,
        excitation_order=2,
        noise_order=3,
        firewall_mode="positive",
    )
    cosine_passed, _stage, cosine_details = SemanticFirewall.run_cosine_filter(query, corpus, cfg)
    assert cosine_passed is True
    assert cosine_details["cosine_sim"] == pytest.approx(0.85, abs=1e-6)

    result = SemanticFirewall.evaluate_clause(
        query.astype(np.float32),
        corpus.astype(np.float32),
        cfg,
        word_count=12,
    )
    assert result["passed"] is False
    assert result["breach_reason"] == "excitation_mass"
    assert [entry["stage"] for entry in result["trace"]] == ["cosine", "excitation"]
    assert result["trace"][0]["passed"] is True
    assert result["trace"][1]["activations"] == 2
    assert result["trace"][1]["passed"] is False


def test_boundary_delta_is_not_rounded_into_tolerance():
    raw = 0.01504
    assert round(raw, 4) <= EPSILON
    assert float(np.float32(raw)) > float(np.float32(EPSILON))
    deltas = np.zeros(DIM, dtype=np.float32)
    deltas[0] = np.float32(raw)
    query, corpus = _pair_with_deltas(deltas)
    cfg = ConfigState(noise_tolerance=EPSILON, excitation_threshold=DIM)
    _passed, _stage, details = SemanticFirewall.run_excitation_filter(
        query, corpus, cfg, word_count=10
    )
    assert details["activations"] == DIM - 1


def test_short_query_decays_epsilon_without_stepping_tau():
    cfg = ConfigState(noise_tolerance=EPSILON, excitation_threshold=120, firewall_mode="positive")
    negative = ConfigState(
        noise_tolerance=EPSILON,
        excitation_threshold=120,
        firewall_mode="negative",
    )
    zeros = np.zeros(DIM, dtype=np.float32)

    def reading(state: ConfigState, words: int) -> dict:
        return SemanticFirewall.run_excitation_filter(zeros, zeros, state, word_count=words)[2]

    long = reading(cfg, 8)
    mid = reading(cfg, 3)
    short = reading(cfg, 0)
    assert long["epsilon_tolerance"] == EPSILON
    assert short["epsilon_tolerance"] < mid["epsilon_tolerance"] < long["epsilon_tolerance"]
    assert short["epsilon_tolerance"] == EPSILON * math.exp(-1.0)
    assert mid["epsilon_tolerance"] == EPSILON * math.exp(-0.5)
    assert long["threshold"] == mid["threshold"] == short["threshold"] == 120.0
    assert reading(negative, 2)["epsilon_tolerance"] == reading(cfg, 2)["epsilon_tolerance"]
    assert reading(negative, 2)["threshold"] == 120.0


def test_head2_is_the_second_stage_and_defaults_match_coordinate_scale():
    cfg = ConfigState()
    assert cfg.excitation_order == 2
    assert cfg.noise_order == 3
    assert cfg.cosine_order == 1
    assert 120 <= cfg.excitation_threshold <= 200
    assert cfg.noise_tolerance == EPSILON
    aliased = ConfigState(coarse_delta_tolerance=0.02)
    assert aliased.noise_tolerance == 0.02
    names = [name for _order, name, _fn in SemanticFirewall.build_pipeline(cfg)]
    assert names == ["cosine", "excitation", "noise"]
