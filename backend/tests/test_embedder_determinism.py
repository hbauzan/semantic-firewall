"""L01 — embedder determinism harness (stubs always; live BGE-M3 opt-in).

Live probe (N=100, writes the committed report):
    cd backend && uv run python tests/embedder_determinism.py --runs 100
    cd backend && RUN_EMBEDDER_DETERMINISM=1 uv run pytest -q tests/test_embedder_determinism.py
"""
from __future__ import annotations

import os

import numpy as np
import pytest
from app.core.models import ConfigState

from tests.embedder_determinism import (
    LIVE_ENV,
    collect_dense,
    collect_fingerprint,
    first_ingest_chunk,
    load_demo_corpus_body,
    measure_vector_spread,
    measure_verdict_spread,
    render_markdown,
    run_in_process_probe,
)


def test_identical_vectors_are_bit_identical():
    vec = np.linspace(0.0, 1.0, 1024, dtype=np.float32)
    spread = measure_vector_spread([vec, vec.copy(), vec.copy()])
    assert spread.n == 3
    assert spread.dim == 1024
    assert spread.bit_identical is True
    assert spread.unique_hashes == 1
    assert spread.max_abs_delta == 0.0
    assert spread.max_l2_delta == 0.0


def test_jittered_vectors_report_magnitudes():
    base = np.zeros(8, dtype=np.float32)
    noisy = base.copy()
    noisy[3] = np.float32(1e-5)
    spread = measure_vector_spread([base, noisy])
    assert spread.bit_identical is False
    assert spread.unique_hashes == 2
    assert spread.max_abs_delta == pytest.approx(1e-5, rel=1e-6)
    assert spread.max_l2_delta == pytest.approx(1e-5, rel=1e-6)


def test_empty_vector_list_raises():
    with pytest.raises(ValueError, match="at least one"):
        measure_vector_spread([])


def test_mismatched_dimensions_raise():
    with pytest.raises(ValueError, match="dimensions"):
        measure_vector_spread([np.zeros(4, dtype=np.float32), np.zeros(8, dtype=np.float32)])


def test_verdict_stable_when_queries_match_corpus():
    cfg = ConfigState(
        cosine_threshold=0.0,
        excitation_threshold=0,
        global_noise_limit=1.0,
        noise_order=1,
        cosine_order=2,
        excitation_order=3,
    )
    rng = np.random.default_rng(0)
    corpus = rng.random(1024, dtype=np.float32)
    queries = [corpus.copy() for _ in range(5)]
    spread = measure_verdict_spread(
        queries, corpus, cfg, "What is the recommended cold tire pressure?"
    )
    assert spread.n == 5
    assert spread.stable is True
    assert spread.flip_count == 0
    assert spread.unique_passed == (True,)
    assert spread.majority_passed is True


def test_verdict_spread_detects_flips_near_a_real_gate():
    """Aligned vs orthogonal queries against the same corpus must not look stable."""
    cfg = ConfigState(
        cosine_threshold=0.5,
        excitation_threshold=0,
        global_noise_limit=0.0,
        noise_enabled=False,
        cosine_enabled=True,
        excitation_enabled=False,
        cosine_order=1,
        noise_order=2,
        excitation_order=3,
    )
    corpus = np.zeros(1024, dtype=np.float32)
    corpus[0] = 1.0
    aligned = corpus.copy()
    orthogonal = np.zeros(1024, dtype=np.float32)
    orthogonal[1] = 1.0
    spread = measure_verdict_spread(
        [aligned, aligned, orthogonal, orthogonal],
        corpus,
        cfg,
        "tire pressure on the rear axle",
    )
    assert spread.stable is False
    assert spread.flip_count >= 1
    assert set(spread.unique_passed) == {True, False}


def test_collect_dense_calls_embed_full_n_times_in_process():
    calls: list[str] = []

    def _embed(text: str) -> list[float]:
        calls.append(text)
        return [0.25] * 4

    vectors = collect_dense(_embed, "same string", n=7)
    assert calls == ["same string"] * 7
    assert len(vectors) == 7
    assert vectors[0].shape == (4,)


def test_fingerprint_includes_required_runtime_fields():
    fp = collect_fingerprint(embedding_model="BAAI/bge-m3", device="mps", backend_name="st-hybrid-mps")
    assert fp.embedding_model == "BAAI/bge-m3"
    assert fp.device == "mps"
    assert fp.backend_name == "st-hybrid-mps"
    assert fp.sentence_transformers
    assert fp.torch
    assert fp.python
    assert fp.platform
    assert fp.machine


def test_demo_corpus_chunk_is_automotive_domain_without_network():
    body = load_demo_corpus_body("automotive_maintenance.pdf")
    chunk = first_ingest_chunk(body)
    assert "Tire pressure" in chunk or "rear axle" in chunk.lower() or "PSI" in chunk
    assert len(chunk) <= 512


def test_markdown_report_has_magnitudes_not_raw_vectors():
    def _embed(text: str) -> list[float]:
        return [0.1, 0.2, 0.3, 0.4]

    report = run_in_process_probe(
        _embed,
        n=3,
        corpus_text="Tire pressure monitoring is critical for safety. Rear axle nominal PSI is 32.",
        on_corpus_query="What PSI for the rear axle?",
        off_topic_query="How do I bake sourdough bread?",
        cfg=ConfigState(
            cosine_threshold=0.0,
            excitation_threshold=0,
            global_noise_limit=0.0,
            noise_enabled=False,
            cosine_enabled=True,
            excitation_enabled=False,
            cosine_order=1,
            noise_order=2,
            excitation_order=3,
        ),
    )
    md = render_markdown(report)
    assert "N=3" in md or "n=3" in md.lower() or "| 3 |" in md
    assert "max_abs_delta" in md
    assert "BAAI/bge-m3" in md or report.fingerprint.embedding_model in md
    assert "uv run" in md
    assert "Interpretation" in md
    assert "[0.1, 0.2, 0.3" not in md
    roles = {item.prompt_role for item in report.results}
    assert "on_corpus" in roles
    assert "off_topic" in roles
    assert "identity" in roles


@pytest.mark.integration
def test_live_in_process_bge_m3_n100():
    if os.environ.get(LIVE_ENV) != "1":
        pytest.skip(
            f"Set {LIVE_ENV}=1 to run the live N=100 BGE-M3 probe (not part of ./run_tests.sh)."
        )
    from tests.embedder_determinism import run_live_probe, write_report

    report = run_live_probe(n=100)
    assert all(item.vector.n == 100 for item in report.results)
    path = write_report(report)
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "max_abs_delta" in text
    assert report.fingerprint.device in text
