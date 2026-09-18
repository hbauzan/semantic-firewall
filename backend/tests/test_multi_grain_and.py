"""L04 — AND multi-grain lab. Does not call evaluate_clause or chat.py."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from app.modules.geometry.multi_grain import (
    DEFAULT_LEXICAL_MIN_COSINE,
    DEFAULT_MICRO_MIN_COSINE,
    MultiGrainConfig,
    evaluate_sentence,
)
from app.modules.geometry.whitening import fit_whitening
from app.modules.mlx_embedder import EmbeddingOutput

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "multi_grain_sentences.json"

DIM = 8
ON_CORPUS = "The rear axle nominal PSI is 32 when tires are cold."
OFF_TOPIC = "What are the best mutual fund allocations for retirement planning?"


def _vec(*ones_at: int) -> list[float]:
    v = np.zeros(DIM, dtype=np.float64)
    for i in ones_at:
        v[i] = 1.0
    n = np.linalg.norm(v)
    return (v / n).tolist() if n else v.tolist()


def _nodes() -> list[dict]:
    para = {
        "node_id": "p1",
        "pack_id": "lab-automotive",
        "grain": "paragraph",
        "parent_id": "s1",
        "text": "Tire pressure. The rear axle nominal PSI is 32.",
        "vector": _vec(0, 1),
        "sparse": {10: 1.0, 11: 0.8, 12: 0.5},
    }
    decoy_para = {
        "node_id": "p2",
        "pack_id": "lab-automotive",
        "grain": "paragraph",
        "parent_id": "s1",
        "text": "Coolant system maintenance includes thermostat testing.",
        "vector": _vec(4, 5),
        "sparse": {90: 1.0},
    }
    sent = {
        "node_id": "t1",
        "pack_id": "lab-automotive",
        "grain": "sentence",
        "parent_id": "p1",
        "text": ON_CORPUS,
        "vector": _vec(0),
        "sparse": {10: 1.0, 11: 0.7},
    }
    decoy_sent = {
        "node_id": "t2",
        "pack_id": "lab-automotive",
        "grain": "sentence",
        "parent_id": "p2",
        "text": "Coolant system maintenance includes thermostat testing.",
        "vector": _vec(4),
        "sparse": {90: 1.0},
    }
    return [para, decoy_para, sent, decoy_sent]


def _embed_on_corpus(_text: str) -> EmbeddingOutput:
    return EmbeddingOutput(dense=_vec(0), sparse={10: 1.0, 11: 0.6})


def _embed_lexical_fail(_text: str) -> EmbeddingOutput:
    return EmbeddingOutput(dense=_vec(0), sparse={77: 1.0, 88: 1.0})


def _embed_off_topic(_text: str) -> EmbeddingOutput:
    return EmbeddingOutput(dense=_vec(7), sparse={99: 1.0})


def test_golden_fixture_lists_the_three_required_cases():
    payload = json.loads(FIXTURE.read_text(encoding="utf-8"))
    ids = {c["id"] for c in payload["cases"]}
    assert ids == {"on_corpus", "lexical_fail", "off_topic"}
    assert payload["pack_id"] == "lab-automotive"


def test_and_passes_when_all_three_legs_pass():
    verdict = evaluate_sentence(
        ON_CORPUS,
        "lab-automotive",
        nodes=_nodes(),
        embed_fn=_embed_on_corpus,
    )
    assert verdict.passed is True
    assert verdict.reason is None
    assert verdict.micro.passed and verdict.meso.passed and verdict.lexical.passed
    assert verdict.micro.score >= DEFAULT_MICRO_MIN_COSINE
    assert verdict.lexical.score >= DEFAULT_LEXICAL_MIN_COSINE
    assert verdict.micro.node_id == "t1"
    assert verdict.meso.node_id == "p1"


def test_and_fails_lexical_when_sparse_is_disjoint():
    verdict = evaluate_sentence(
        ON_CORPUS,
        "lab-automotive",
        nodes=_nodes(),
        embed_fn=_embed_lexical_fail,
    )
    assert verdict.passed is False
    assert verdict.reason == "lexical"
    assert verdict.micro.passed is True
    assert verdict.meso.passed is True
    assert verdict.lexical.passed is False


def test_off_topic_fails_micro_without_alpha_rescue():
    verdict = evaluate_sentence(
        OFF_TOPIC,
        "lab-automotive",
        nodes=_nodes(),
        embed_fn=_embed_off_topic,
    )
    assert verdict.passed is False
    assert verdict.reason == "micro"
    assert verdict.micro.passed is False
    assert verdict.micro.score < DEFAULT_MICRO_MIN_COSINE


def test_meso_fails_when_nearest_paragraph_is_not_the_parent():
    nodes = _nodes()
    for node in nodes:
        if node["node_id"] == "p2":
            node["vector"] = _vec(0, 1)
        if node["node_id"] == "p1":
            node["vector"] = _vec(6)
    verdict = evaluate_sentence(
        ON_CORPUS,
        "lab-automotive",
        nodes=nodes,
        embed_fn=_embed_on_corpus,
    )
    assert verdict.passed is False
    assert verdict.reason == "meso"
    assert verdict.micro.passed is True
    assert verdict.meso.passed is False


def test_thresholds_live_in_config_not_magic_scatter():
    tight = MultiGrainConfig(micro_min_cosine=0.999, lexical_min_cosine=0.999)
    verdict = evaluate_sentence(
        ON_CORPUS,
        "lab-automotive",
        nodes=_nodes(),
        embed_fn=_embed_on_corpus,
        config=tight,
    )
    assert verdict.passed is False
    assert verdict.reason in {"micro", "lexical"}


def test_whitening_seam_does_not_change_conjunction_shape():
    nodes = _nodes()
    matrix = np.stack([np.asarray(n["vector"], dtype=np.float64) for n in nodes])
    model = fit_whitening(matrix, corpus_id="lab-automotive")
    verdict = evaluate_sentence(
        ON_CORPUS,
        "lab-automotive",
        nodes=nodes,
        embed_fn=_embed_on_corpus,
        whitening=model,
    )
    assert verdict.micro.passed is True
    assert "micro" in verdict.as_dict()
    assert verdict.as_dict()["passed"] is True
