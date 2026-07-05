"""Tests for hybrid firewall phases 1-5."""
import asyncio
import math

import numpy as np
import pytest

from app.core.exceptions import BurstDetectionBreach
from app.core.firewall import SemanticFirewall
from app.core.models import ConfigState
from app.modules.dispatcher import UnifiedInferenceDispatcher
from app.modules.mlx_embedder import SafeSparsePooling
from app.modules.storage import (
    Storage,
    compute_rabitq_fields,
    deserialize_sparse,
    hamming_distance,
    pack_binary_signature as storage_pack,
    serialize_sparse,
)


def test_calculate_raw_entropy_low_for_repetitive_chars():
    entropy = SemanticFirewall.calculate_raw_entropy("!!!!!!!!!!")
    assert entropy < 1.0


def test_calculate_raw_entropy_high_for_diverse_text():
    text = "The quick brown fox jumps over the lazy dog 0123456789"
    entropy = SemanticFirewall.calculate_raw_entropy(text)
    assert entropy > 3.0


def test_burst_detection_breach_exception_fields():
    exc = BurstDetectionBreach("!!!", 0.5, 4.5)
    assert exc.breach_type == "BURST_DETECTION_BREACH"
    assert exc.entropy == 0.5
    assert exc.limit == 4.5


def test_sparse_serialize_round_trip():
    sparse = {1: 0.8, 42: 0.3}
    raw = serialize_sparse(sparse)
    assert isinstance(raw, str)
    restored = deserialize_sparse(raw)
    assert restored == sparse


def test_pack_binary_signature_is_128_bytes():
    vec = np.random.randn(1024).astype(np.float32)
    packed = storage_pack(vec)
    assert len(packed) == 128


def test_hamming_distance_zero_for_identical_signatures():
    vec = np.ones(1024, dtype=np.float32)
    sig = storage_pack(vec)
    assert hamming_distance(sig, sig) == 0


def test_hamming_distance_counts_bit_flips():
    a = bytes([0b00000000])
    b = bytes([0b00001111])
    assert hamming_distance(a, b) == 4


def test_hamming_fallback_matches_popcount():
    a = storage_pack(np.random.randn(1024).astype(np.float32))
    b = storage_pack(np.random.randn(1024).astype(np.float32))
    from app.modules.storage import _hamming_popcount_fallback
    assert hamming_distance(a, b) == _hamming_popcount_fallback(a, b)


def test_compute_rabitq_fields_shape():
    vec = [0.1] * 1024
    fields = compute_rabitq_fields(vec)
    assert len(fields["vector_packed"]) == 128
    assert fields["centroid_distance"] > 0
    assert isinstance(fields["quantization_projection"], float)


def test_rabitq_composite_score_prefers_projection(monkeypatch):
    storage = Storage.__new__(Storage)
    storage.rabitq_w = 1.0
    storage.hamming_prefilter_max = 512
    row_low = {"quantization_projection": 0.1}
    row_high = {"quantization_projection": 0.9}
    assert storage._composite_score(100, row_high) < storage._composite_score(100, row_low)


def test_compute_alpha_in_unit_interval():
    alpha = SemanticFirewall.compute_alpha("What is the recommended tire pressure?")
    assert 0.0 < alpha < 1.0


def test_compute_epsilon_contracts_with_complexity():
    base = 0.005
    simple = SemanticFirewall.compute_epsilon("hi", base)
    complex_ = SemanticFirewall.compute_epsilon(
        "Explain the complete maintenance schedule for turbocharged engines in detail",
        base,
    )
    assert complex_ < simple


def test_lexical_density_bounds():
    density = SemanticFirewall.lexical_density("running quickly through mountains")
    assert 0.0 <= density <= 1.0


def test_sparse_short_circuit_blocks_low_similarity():
    cfg = ConfigState(cosine_threshold=0.8, firewall_mode="positive")
    q_sparse = {1: 1.0, 2: 0.5}
    c_sparse = {99: 1.0, 100: 0.5}
    passed, stage, details = SemanticFirewall.run_sparse_short_circuit(
        q_sparse, c_sparse, cfg, query_text="test query text",
    )
    assert stage == "sparse"
    assert passed is False
    assert details["sparse_sim"] == 0.0


def test_evaluate_clause_hybrid_trace_with_sparse():
    cfg = ConfigState(cosine_threshold=0.0, excitation_threshold=0, global_noise_limit=1.0)
    vec = np.random.rand(1024).astype(np.float32)
    q_sparse = {1: 1.0, 2: 0.5}
    c_sparse = {1: 0.9, 2: 0.4}
    result = SemanticFirewall.evaluate_clause(
        vec, vec, cfg, word_count=10,
        query_text="What is the tire pressure for this vehicle?",
        q_sparse=q_sparse, c_sparse=c_sparse,
    )
    stages = [t["stage"] for t in result["trace"]]
    assert "sparse" in stages
    sparse_trace = next(t for t in result["trace"] if t["stage"] == "sparse")
    assert sparse_trace["sparse_sim"] > 0.0


def test_safe_sparse_pooling_numpy_fallback():
    pool = SafeSparsePooling()
    projections = np.array([[0.0, 2.0], [1.0, 0.5]], dtype=np.float32)
    pooled = pool.pool_token_projections(projections)
    assert pooled.shape == (2,)
    assert pooled[0] == 1.0
    assert pooled[1] == 2.0


@pytest.mark.asyncio
async def test_dispatcher_serializes_concurrent_requests(monkeypatch):
    calls: list[str] = []

    class FakeEmbedder:
        backend_name = "st-hybrid-mps"

        def embed_full(self, text: str):
            calls.append(text)
            from app.modules.mlx_embedder import EmbeddingOutput
            return EmbeddingOutput(dense=[0.1] * 4, sparse=None)

    dispatcher = UnifiedInferenceDispatcher(embedder=FakeEmbedder())
    loop = asyncio.get_running_loop()
    dispatcher.start(loop)

    results = await asyncio.gather(
        dispatcher.submit_inference("a"),
        dispatcher.submit_inference("b"),
        dispatcher.submit_inference("c"),
    )
    dispatcher.stop()

    assert len(results) == 3
    assert calls == ["a", "b", "c"]


@pytest.mark.asyncio
async def test_dispatcher_high_concurrency_serial_order():
    calls: list[str] = []

    class FakeEmbedder:
        backend_name = "st-hybrid-cpu"

        def embed_full(self, text: str):
            calls.append(text)
            from app.modules.mlx_embedder import EmbeddingOutput
            return EmbeddingOutput(dense=[0.1] * 4, sparse={1: 1.0})

    dispatcher = UnifiedInferenceDispatcher(embedder=FakeEmbedder())
    loop = asyncio.get_running_loop()
    dispatcher.start(loop)

    texts = [f"req-{i}" for i in range(20)]
    results = await asyncio.gather(*(dispatcher.submit_inference(t) for t in texts))
    dispatcher.stop()

    assert len(results) == 20
    assert calls == texts


@pytest.mark.asyncio
async def test_dispatcher_pytorch_uses_to_thread(monkeypatch):
    calls: list[str] = []

    class FakeEmbedder:
        backend_name = "legacy-cpu"

        def embed_full(self, text: str):
            calls.append(text)
            from app.modules.mlx_embedder import EmbeddingOutput
            return EmbeddingOutput(dense=[0.2] * 4, sparse=None)

    dispatcher = UnifiedInferenceDispatcher(embedder=FakeEmbedder())
    loop = asyncio.get_running_loop()
    dispatcher.start(loop)

    result = await dispatcher.submit_inference("sync-path")
    dispatcher.stop()

    assert result.dense == [0.2] * 4
    assert calls == ["sync-path"]


def test_burst_detection_blocks_repetitive_prompt_via_proxy():
    """Phase 1: raw entropy CPU discard blocks before embedding."""
    from tests.conftest import client
    from app.core.state import set_config_sync as set_config

    set_config(raw_entropy_limit=3.0, noise_enabled=True)
    res = client.post(
        "/v1/chat/completions",
        json={
            "model": "llama3.1",
            "messages": [{"role": "user", "content": "!!!!!!!!!!"}],
            "stream": True,
        },
    )
    assert res.status_code == 403
    data = res.json()
    assert data["error"]["type"] == "security_breach"
    assert data["error"].get("breach_type") == "BURST_DETECTION_BREACH"
