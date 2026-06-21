"""Engine Unit Tests — pure firewall math, zero HTTP dependencies.

Tests for SemanticFirewall: segmentation, filters, pipeline, mode logic.
Partitioned from perform_tests.py (Finding Q5).
"""
import pytest
import numpy as np
from app.core.models import ConfigState
from app.core.state import set_config_sync as set_config
from app.core.firewall import SemanticFirewall


# --- Segmentation ---

def test_engine_segment_basic():
    """SemanticFirewall.segment splits on punctuation and chunks long clauses."""
    clauses = SemanticFirewall.segment("Hello world. How are you? Fine thanks")
    assert len(clauses) >= 2

def test_engine_segment_overflow_chunking():
    """Clauses over 20 words get force-split into 15-word sub-chunks."""
    long_text = " ".join(["word"] * 30)
    clauses = SemanticFirewall.segment(long_text)
    for c in clauses:
        assert len(c.split()) <= 15


# --- evaluate_clause ---

def test_engine_evaluate_clause_all_pass():
    """Identical vectors must pass all filters (entropy floor low enough for natural vectors)."""
    cfg = ConfigState(cosine_threshold=0.0, excitation_threshold=0, global_noise_limit=1.0)
    vec = np.random.rand(1024).astype(np.float32)
    result = SemanticFirewall.evaluate_clause(vec, vec, cfg, word_count=10)
    assert result["passed"] is True
    assert result["breach_reason"] is None
    assert len(result["trace"]) == 3

def test_engine_evaluate_clause_noise_breach():
    """Sparse vector with high entropy floor must breach on noise filter."""
    cfg = ConfigState(
        cosine_threshold=0.0, excitation_threshold=0,
        global_noise_limit=10.0, noise_order=1, cosine_order=2, excitation_order=3
    )  # Entropy floor = 10.0 -> no natural/sparse vector reaches this
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0  # Single spike -> minimal entropy
    c = np.zeros(1024, dtype=np.float32)
    result = SemanticFirewall.evaluate_clause(q, c, cfg, word_count=10)
    assert result["passed"] is False
    assert result["breach_reason"] == "noise"
    # Only noise ran (order=1 breached), so trace has 1 entry
    assert len(result["trace"]) == 1


# --- Filter Enable/Disable ---

def test_disabled_filter_skipped_in_pipeline():
    """A disabled filter must not appear in the pipeline trace."""
    cfg = ConfigState(
        cosine_threshold=0.0, excitation_threshold=0, global_noise_limit=10.0,
        noise_enabled=False  # Noise disabled
    )
    vec = np.random.rand(1024).astype(np.float32)
    result = SemanticFirewall.evaluate_clause(vec, vec, cfg, word_count=10)
    assert result["passed"] is True
    stage_names = [t["stage"] for t in result["trace"]]
    assert "noise" not in stage_names
    assert "cosine" in stage_names
    assert "excitation" in stage_names
    assert len(result["trace"]) == 2

def test_all_filters_disabled_bypasses_firewall():
    """With all filters disabled, pipeline is empty and clause passes trivially."""
    cfg = ConfigState(
        noise_enabled=False, cosine_enabled=False, excitation_enabled=False
    )
    vec = np.random.rand(1024).astype(np.float32)
    result = SemanticFirewall.evaluate_clause(vec, vec, cfg, word_count=10)
    assert result["passed"] is True
    assert len(result["trace"]) == 0


# --- ConfigState Validation ---

def test_adaptive_factor_default():
    """Default adaptive_factor should be 0.85 on fresh ConfigState."""
    fresh = ConfigState()
    assert fresh.adaptive_factor == 0.85

def test_config_state_is_immutable():
    """Frozen ConfigState must reject direct attribute mutation."""
    cfg = ConfigState()
    with pytest.raises(Exception):
        cfg.excitation_threshold = 999

def test_duplicate_pipeline_orders_rejected():
    """ConfigState must reject duplicate order values."""
    with pytest.raises(ValueError, match="unique"):
        ConfigState(cosine_order=1, excitation_order=1, noise_order=2)

def test_config_validation_out_of_range():
    """ConfigState must reject values outside defined bounds."""
    with pytest.raises(Exception):
        ConfigState(excitation_threshold=2000)  # max 1024
    with pytest.raises(Exception):
        ConfigState(adaptive_factor=5.0)  # max 1.0
    with pytest.raises(Exception):
        ConfigState(cosine_order=0)  # min 1


# --- Firewall Mode ---

def test_firewall_mode_default_is_positive():
    """Default firewall_mode must be 'positive' on fresh ConfigState."""
    fresh = ConfigState()
    assert fresh.firewall_mode == "positive"

def test_firewall_mode_rejects_invalid_value():
    """ConfigState must reject firewall_mode values other than 'positive'/'negative'."""
    with pytest.raises(Exception):
        ConfigState(firewall_mode="neutral")

def test_engine_negative_mode_identical_vectors_breach():
    """Negative mode: identical vectors (max similarity) must BREACH on first filter."""
    cfg = ConfigState(
        cosine_threshold=0.0, excitation_threshold=0, global_noise_limit=1.0,
        firewall_mode="negative"
    )
    vec = np.random.rand(1024).astype(np.float32)
    result = SemanticFirewall.evaluate_clause(vec, vec, cfg, word_count=10)
    assert result["passed"] is False
    assert result["breach_reason"] == "negative:cosine"
    assert result["trace"][1]["passed"] is False

def test_engine_negative_mode_divergent_vectors_pass():
    """Negative mode: orthogonal vectors (low similarity) must PASS."""
    cfg = ConfigState(
        cosine_threshold=0.5, excitation_threshold=500, global_noise_limit=0.01,
        noise_order=1, cosine_order=2, excitation_order=3,
        firewall_mode="negative"
    )
    q = np.ones(1024, dtype=np.float32)
    c = np.zeros(1024, dtype=np.float32)
    result = SemanticFirewall.evaluate_clause(q, c, cfg, word_count=10)
    assert result["passed"] is True
    assert result["breach_reason"] is None

def test_engine_positive_mode_identical_vectors_pass():
    """Positive mode: identical vectors must PASS (baseline)."""
    cfg = ConfigState(
        cosine_threshold=0.0, excitation_threshold=0, global_noise_limit=1.0,
        firewall_mode="positive"
    )
    vec = np.random.rand(1024).astype(np.float32)
    result = SemanticFirewall.evaluate_clause(vec, vec, cfg, word_count=10)
    assert result["passed"] is True


# --- RAG Top-K ---

def test_rag_top_k_default():
    """Default rag_top_k should be 3 on fresh ConfigState."""
    fresh = ConfigState()
    assert fresh.rag_top_k == 3

def test_rag_top_k_validation():
    """rag_top_k must reject values outside 1-10."""
    with pytest.raises(Exception):
        ConfigState(rag_top_k=0)
    with pytest.raises(Exception):
        ConfigState(rag_top_k=11)


# --- Adaptive Inversion ---

def test_adaptive_inversion_negative_mode():
    """Verify that Negative Mode increases strictness (1.15x) for short queries."""
    set_config(firewall_mode="negative", excitation_threshold=100, adaptive_factor=0.85)
    q = np.random.rand(1024).astype(np.float32)
    c = q.copy()
    c[110:] = q[110:] + 1.0
    from app.core.state import config_state
    result = SemanticFirewall.run_excitation_filter(q, c, config_state, word_count=2)
    assert abs(result[2]["threshold"] - 115.0) < 0.001


# --- Shannon Entropy ---

def test_entropy_low_for_collapsed_vector():
    """A sparse (single-spike) vector must produce low entropy below 4.5 threshold."""
    cfg = ConfigState(global_noise_limit=4.5)
    q = np.zeros(1024, dtype=np.float32)
    q[0] = 1.0  # Single peak -> entropy near 0
    c = np.zeros(1024, dtype=np.float32)
    passed, stage, details = SemanticFirewall.run_noise_filter(q, c, cfg)
    assert passed is False, f"Sparse vector should breach, got entropy={details.get('entropy')}"
    assert stage == "noise"
    assert details["entropy"] < 4.5

def test_entropy_high_for_natural_vector():
    """A random natural-distribution vector must produce high entropy above 4.5 threshold."""
    cfg = ConfigState(global_noise_limit=4.5)
    np.random.seed(42)
    q = np.random.rand(1024).astype(np.float32)
    c = np.zeros(1024, dtype=np.float32)
    passed, stage, details = SemanticFirewall.run_noise_filter(q, c, cfg)
    assert passed is True, f"Natural vector should pass, got entropy={details.get('entropy')}"
    assert stage == "noise"
    assert details["entropy"] > 4.5
