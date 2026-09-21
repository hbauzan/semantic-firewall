"""Head 1 — cosine difference macro gate.

Positive mode passes only when cos(Q, C) >= tau_cos, which is the same cut as
angular distance (1 - cos) <= 1 - tau_cos. A breach stops the pipeline before
excitation and noise run.
"""
from __future__ import annotations

import math

import numpy as np
import pytest
from pydantic import ValidationError

from app.core.firewall import SemanticFirewall
from app.core.models import ConfigState, ConfigUpdate

DIM = 1024
TAU = 0.5315


def _axis(index: int, dtype=np.float64) -> np.ndarray:
    vector = np.zeros(DIM, dtype=dtype)
    vector[index] = 1.0
    return vector


def _prisma_pair() -> tuple[np.ndarray, np.ndarray]:
    """Unit corpus direction and an out-of-domain query orthogonal to it."""
    rng = np.random.default_rng(2026)
    corpus = rng.standard_normal(DIM).astype(np.float64)
    corpus /= np.linalg.norm(corpus)
    query = rng.standard_normal(DIM).astype(np.float64)
    query -= np.dot(query, corpus) * corpus
    query /= np.linalg.norm(query)
    return query, corpus


def test_identical_vectors_pass_with_zero_distance():
    cfg = ConfigState(cosine_threshold=TAU)
    vector = _axis(0)
    passed, stage, details = SemanticFirewall.run_cosine_filter(vector, vector, cfg)
    assert passed is True
    assert stage == "cosine"
    assert details["cosine_sim"] == 1.0
    assert details["cosine_distance"] == 0.0


def test_orthogonal_vectors_breach_under_positive_mode():
    cfg = ConfigState(cosine_threshold=TAU, firewall_mode="positive")
    passed, stage, details = SemanticFirewall.run_cosine_filter(_axis(0), _axis(1), cfg)
    assert passed is False
    assert stage == "cosine"
    assert details["cosine_sim"] == 0.0
    assert details["cosine_distance"] == 1.0


def test_prisma_ood_query_breaches_at_stage_one():
    query, corpus = _prisma_pair()
    cfg = ConfigState(cosine_threshold=TAU, firewall_mode="positive")
    result = SemanticFirewall.evaluate_clause(query, corpus, cfg, word_count=12)
    assert result["passed"] is False
    assert result["breach_reason"] == "cosine"
    assert result["trace"][0]["stage"] == "cosine"
    assert result["trace"][0]["passed"] is False
    assert result["trace"][0]["cosine_sim"] < TAU
    assert result["trace"][0]["cosine_distance"] == 1.0 - result["trace"][0]["cosine_sim"]


def test_head1_breach_skips_head2_and_head3():
    cfg = ConfigState()
    pipeline = SemanticFirewall.build_pipeline(cfg)
    assert pipeline[0][0] == 1
    assert pipeline[0][1] == "cosine"

    result = SemanticFirewall.evaluate_clause(_axis(0), _axis(1), cfg, word_count=12)
    stages = [entry["stage"] for entry in result["trace"]]
    assert result["passed"] is False
    assert result["breach_reason"] == "cosine"
    assert stages == ["cosine"]


def test_zero_norm_breaches_immediately():
    cfg = ConfigState()
    query = np.zeros(DIM, dtype=np.float64)
    result = SemanticFirewall.evaluate_clause(query, _axis(3), cfg, word_count=12)
    assert result["passed"] is False
    assert result["breach_reason"] == "zero_norm"
    assert [entry["stage"] for entry in result["trace"]] == ["cosine"]
    assert result["breach_details"]["error"] == "zero_norm"
    assert result["breach_details"]["cosine_sim"] == 0.0
    assert result["breach_details"]["cosine_distance"] == 1.0


def test_cosine_reading_is_clipped_and_unrounded():
    target = 0.5315123456789012
    query = np.zeros(DIM, dtype=np.float64)
    query[0] = target
    query[1] = math.sqrt(1.0 - target * target)
    corpus = _axis(0)
    cfg = ConfigState(cosine_threshold=TAU)
    passed, _stage, details = SemanticFirewall.run_cosine_filter(query, corpus, cfg)
    assert passed is True
    assert details["cosine_sim"] == pytest.approx(target, abs=1e-12)
    assert details["cosine_sim"] != round(details["cosine_sim"], 4)
    assert details["cosine_distance"] == 1.0 - details["cosine_sim"]

    clipped, _stage, clipped_details = SemanticFirewall.run_cosine_filter(
        query, corpus, cfg, hybrid_score=1.5
    )
    assert clipped is True
    assert clipped_details["cosine_sim"] == 1.0
    assert clipped_details["cosine_distance"] == 0.0


def test_cosine_threshold_is_closed_unit_interval():
    ConfigState(cosine_threshold=0.0)
    ConfigState(cosine_threshold=1.0)
    with pytest.raises(ValidationError):
        ConfigState(cosine_threshold=-1e-15)
    with pytest.raises(ValidationError):
        ConfigState(cosine_threshold=1.0 + 1e-15)
    with pytest.raises(ValidationError):
        ConfigUpdate(
            excitation_threshold=150,
            noise_tolerance=0.005,
            cosine_threshold=1.5,
        )


def test_default_cosine_order_is_first_gate():
    cfg = ConfigState()
    assert cfg.cosine_order == 1
    names = [name for _order, name, _fn in SemanticFirewall.build_pipeline(cfg)]
    assert names[0] == "cosine"
