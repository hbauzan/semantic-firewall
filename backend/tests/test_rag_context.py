"""Unit tests for multi-clause RAG context accumulation."""
import pytest
from app.core.models import ConfigState
from app.modules.rag_context import accumulate_rag_chunks, join_rag_context


def test_rag_top_k_default():
    """Default rag_top_k should be 12 on fresh ConfigState."""
    fresh = ConfigState()
    assert fresh.rag_top_k == 12


def test_rag_top_k_validation():
    """rag_top_k must reject values outside 1-32."""
    with pytest.raises(Exception):
        ConfigState(rag_top_k=0)
    with pytest.raises(Exception):
        ConfigState(rag_top_k=33)


def test_accumulate_merges_two_clause_result_sets():
    """Chunks from two clauses are unioned; shared ids appear once."""
    chunks: list[str] = []
    seen: set = set()

    clause_a = [
        {"id": 1, "text": "alpha section"},
        {"id": 2, "text": "beta section"},
    ]
    clause_b = [
        {"id": 2, "text": "beta section"},
        {"id": 3, "text": "gamma section"},
    ]

    assert accumulate_rag_chunks(clause_a, chunks, seen) == 2
    assert accumulate_rag_chunks(clause_b, chunks, seen) == 1
    assert chunks == ["alpha section", "beta section", "gamma section"]
    assert join_rag_context(chunks) == "alpha section\n---\nbeta section\n---\ngamma section"


def test_accumulate_dedupes_by_text_when_id_missing():
    chunks: list[str] = []
    seen: set = set()
    accumulate_rag_chunks([{"text": "same"}], chunks, seen)
    accumulate_rag_chunks([{"text": "same"}], chunks, seen)
    assert chunks == ["same"]
