"""Unit tests for Dynamic Concept-Clustered Dataset Generator."""
import numpy as np
import pytest
from app.modules.dataset_generator import (
    compute_coverage_counts,
    cluster_chunk_texts,
    generate_dataset_for_pack,
)


def test_compute_coverage_counts_scaling():
    """Verify coverage counts scale correctly with N chunks across all modes."""
    # Micro corpus (5 chunks)
    k_fast, off_fast, pig_fast, adv_fast = compute_coverage_counts(5, mode="fast")
    assert 3 <= k_fast <= 6
    assert off_fast == 4

    k_rec, off_rec, pig_rec, adv_rec = compute_coverage_counts(5, mode="recommended")
    assert 8 <= k_rec <= 30

    k_exh, off_exh, pig_exh, adv_exh = compute_coverage_counts(5, mode="exhaustive")
    assert k_exh >= 15

    # Large corpus (500 chunks)
    k_rec_large, _, _, _ = compute_coverage_counts(500, mode="recommended")
    k_exh_large, _, _, _ = compute_coverage_counts(500, mode="exhaustive")
    assert k_exh_large > k_rec_large


def test_cluster_chunk_texts_kmeans():
    """Verify pure numpy vector K-Means clustering groups embeddings into distinct centroids."""
    rows = []
    # Create 3 distinct vector clusters
    for i in range(10):
        vec = [1.0 if j == 0 else 0.01 for j in range(1024)]
        rows.append({"text": f"Cluster A Chunk {i}", "vector": vec})
    for i in range(10):
        vec = [1.0 if j == 500 else 0.01 for j in range(1024)]
        rows.append({"text": f"Cluster B Chunk {i}", "vector": vec})
    for i in range(10):
        vec = [1.0 if j == 1023 else 0.01 for j in range(1024)]
        rows.append({"text": f"Cluster C Chunk {i}", "vector": vec})

    representatives = cluster_chunk_texts(rows, k=3)
    assert len(representatives) == 3
    # Check that representative texts originate from valid rows
    all_texts = {r["text"] for r in rows}
    for rep in representatives:
        assert rep in all_texts
