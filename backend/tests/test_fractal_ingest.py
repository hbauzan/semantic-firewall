"""L03 — lab pyramid ingest. Does not call evaluate_clause or POST /corpus/upload-pdf."""
from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path

import lancedb
import numpy as np
import pyarrow as pa
import pytest

from app.modules.fractal_ingest import (
    GRAINS,
    PYRAMID_TABLE,
    VECTOR_DIM,
    PageText,
    build_pyramid,
    extract_pages,
    ingest_pdf,
    join_pages,
    load_pyramid,
    persist_pyramid,
)
from app.modules.ingestor import chunk_text
from app.modules.mlx_embedder import EmbeddingOutput


def _load_demo_corpora_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "generate_demo_corpora.py"
    spec = importlib.util.spec_from_file_location("generate_demo_corpora", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def stub_embed(text: str) -> EmbeddingOutput:
    """Deterministic fake BGE-M3. Tests must not load a second SentenceTransformer."""
    seed = int.from_bytes(hashlib.sha256(text.encode("utf-8")).digest()[:8], "little")
    rng = np.random.default_rng(seed)
    vec = rng.normal(size=VECTOR_DIM).astype(np.float32)
    vec /= np.linalg.norm(vec) + 1e-9
    tokens = [t for t in text.split() if t]
    sparse = {i: 1.0 for i in range(min(3, len(tokens)))}
    return EmbeddingOutput(dense=vec.tolist(), sparse=sparse)


FIXTURE_PAGES = (
    PageText(
        page=1,
        text=(
            "Vehicle Maintenance Reference\n\n"
            "Tire pressure monitoring is critical for safety. The rear axle nominal PSI is 32.\n\n"
            "Brake pad inspection should occur every 12,000 miles."
        ),
    ),
    PageText(
        page=2,
        text=(
            "Coolant system notes\n\n"
            "Coolant system maintenance includes thermostat testing. Overheating traces to a failed thermostat."
        ),
    ),
)


def _nodes_by_grain(nodes):
    grouped: dict[str, list] = {g: [] for g in GRAINS}
    for node in nodes:
        grouped[node.grain].append(node)
    return grouped


def test_grain_is_closed_set():
    nodes = build_pyramid(FIXTURE_PAGES, pack_id="lab-pack", embed_fn=stub_embed)
    assert GRAINS == frozenset({"sentence", "paragraph", "section", "document"})
    assert {n.grain for n in nodes} <= GRAINS
    counts = _nodes_by_grain(nodes)
    assert len(counts["document"]) == 1
    assert len(counts["section"]) == 2
    assert len(counts["paragraph"]) >= 2
    assert len(counts["sentence"]) >= 2


def test_every_sentence_parent_exists_as_paragraph():
    nodes = build_pyramid(FIXTURE_PAGES, pack_id="lab-pack", embed_fn=stub_embed)
    by_id = {n.node_id: n for n in nodes}
    paragraphs = {n.node_id for n in nodes if n.grain == "paragraph"}
    sentences = [n for n in nodes if n.grain == "sentence"]
    assert sentences
    for sent in sentences:
        assert sent.parent_id in paragraphs
        assert by_id[sent.parent_id].grain == "paragraph"


def test_char_span_is_substring_of_joined_source():
    source, _page_spans = join_pages(FIXTURE_PAGES)
    nodes = build_pyramid(FIXTURE_PAGES, pack_id="lab-pack", embed_fn=stub_embed)
    for node in nodes:
        start, end = node.char_span
        assert 0 <= start < end <= len(source)
        assert source[start:end] == node.text


def test_sentences_are_not_prod_512_chunks():
    source, _ = join_pages(FIXTURE_PAGES)
    nodes = build_pyramid(FIXTURE_PAGES, pack_id="lab-pack", embed_fn=stub_embed)
    sentence_texts = [n.text for n in nodes if n.grain == "sentence"]
    assert sentence_texts
    assert sentence_texts != chunk_text(source)
    assert all("." in text or text == text.strip() for text in sentence_texts)
    assert any(len(text) < 120 for text in sentence_texts)


def test_document_vector_is_mean_of_sentence_vectors():
    pages = (
        PageText(page=1, text="Alpha unit sits alone. Bravo unit sits alone."),
    )

    def directional_embed(text: str) -> EmbeddingOutput:
        vec = np.zeros(VECTOR_DIM, dtype=np.float32)
        if text.startswith("Alpha"):
            vec[0] = 1.0
        elif text.startswith("Bravo"):
            vec[1] = 1.0
        else:
            vec[2] = 1.0
        return EmbeddingOutput(dense=vec.tolist(), sparse={0: 1.0})

    nodes = build_pyramid(pages, pack_id="centroid", embed_fn=directional_embed)
    sentences = [n for n in nodes if n.grain == "sentence"]
    document = next(n for n in nodes if n.grain == "document")
    assert len(sentences) == 2
    expected = np.mean([np.asarray(s.vector, dtype=np.float64) for s in sentences], axis=0)
    np.testing.assert_allclose(document.vector, expected, atol=1e-6)


def test_extract_pages_keeps_page_numbers():
    demo = _load_demo_corpora_script()
    pdf_bytes = demo.build_text_pdf(demo.CORPORA["automotive_maintenance.pdf"])
    pages = extract_pages(pdf_bytes)
    assert pages
    assert pages[0].page == 1
    assert all(p.page == i for i, p in enumerate(pages, start=1))
    blob = "\n".join(p.text for p in pages)
    assert "Tire pressure monitoring" in blob


def test_persist_pyramid_does_not_touch_knowledge(tmp_path: Path):
    db_path = tmp_path / "labdb"
    knowledge_schema = pa.schema(
        [
            pa.field("id", pa.int64()),
            pa.field("vector", pa.list_(pa.float32(), VECTOR_DIM)),
            pa.field("text", pa.string()),
            pa.field("metadata", pa.string()),
        ]
    )
    db = lancedb.connect(str(db_path))
    db.create_table(
        "knowledge",
        data=[
            {
                "id": 1,
                "vector": [0.1] * VECTOR_DIM,
                "text": "production-chunk",
                "metadata": '{"filename": "prod.pdf"}',
            }
        ],
        schema=knowledge_schema,
    )

    nodes = build_pyramid(FIXTURE_PAGES, pack_id="lab-pack", embed_fn=stub_embed)
    persist_pyramid(nodes, db_path)

    tables = db.list_tables()
    table_names = tables.tables if hasattr(tables, "tables") else list(tables)
    assert "knowledge" in table_names
    assert PYRAMID_TABLE in table_names
    knowledge_rows = db.open_table("knowledge").search().to_list()
    assert len(knowledge_rows) == 1
    assert knowledge_rows[0]["text"] == "production-chunk"

    loaded = load_pyramid(db_path, pack_id="lab-pack")
    assert {row["grain"] for row in loaded} == GRAINS
    paragraph_ids = {row["node_id"] for row in loaded if row["grain"] == "paragraph"}
    for row in loaded:
        if row["grain"] == "sentence":
            assert row["parent_id"] in paragraph_ids
        start, end = row["char_span"]
        assert isinstance(start, int) and isinstance(end, int)


def test_ingest_pdf_roundtrip_with_demo_bytes(tmp_path: Path):
    demo = _load_demo_corpora_script()
    pdf_bytes = demo.build_text_pdf(demo.CORPORA["automotive_maintenance.pdf"])
    nodes = ingest_pdf(
        pdf_bytes,
        pack_id="automotive_maintenance",
        embed_fn=stub_embed,
        db_path=tmp_path / "labdb",
    )
    grains = {n.grain for n in nodes}
    assert grains == GRAINS
    loaded = load_pyramid(tmp_path / "labdb", pack_id="automotive_maintenance")
    assert len(loaded) == len(nodes)


def test_empty_pages_raise():
    with pytest.raises(ValueError, match="empty"):
        build_pyramid((), pack_id="empty", embed_fn=stub_embed)
