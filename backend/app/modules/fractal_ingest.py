"""Lab pyramid ingest: four grains + lineage in LanceDB table ``knowledge_pyramid``.

Does not replace production ``chunk_text`` / ``POST /corpus/upload-pdf``.
Does not write the ``knowledge`` table. Embedder is injected by the caller.

Document grain vector = mean of sentence dense vectors (same space as micro
inspection). Embedding the concatenated PDF would mix a different token scale
into the global node; the centroid of the pyramid's sentences is the claim.

Page breaks are the section proxy when the PDF has no outline. ``char_span`` is
half-open ``[start, end)`` into the concatenated page text (pages joined by
``\\n\\n``).

Ingest the automotive demo pack:

    cd backend && uv run python -m app.modules.fractal_ingest --corpus automotive
"""
from __future__ import annotations

import argparse
import importlib.util
import io
import json
import logging
import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import lancedb
import numpy as np
import pyarrow as pa
from pypdf import PdfReader

logger = logging.getLogger(__name__)

GRAINS = frozenset({"sentence", "paragraph", "section", "document"})
PYRAMID_TABLE = "knowledge_pyramid"
VECTOR_DIM = 1024
DEMO_CORPUS_FILE = "automotive_maintenance.pdf"
DEFAULT_DB_PATH = Path(__file__).resolve().parents[2] / "lancedb_data"
PAGE_JOIN = "\n\n"

_PACK_ID_RE = re.compile(r"^[\w.\-]+$")
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")
_PARA_SPLIT = re.compile(r"\n\n+")

EmbedFn = Callable[[str], Any]

pyramid_schema = pa.schema(
    [
        pa.field("node_id", pa.string()),
        pa.field("pack_id", pa.string()),
        pa.field("grain", pa.string()),
        pa.field("parent_id", pa.string()),
        pa.field("section_id", pa.string()),
        pa.field("page", pa.int64()),
        pa.field("char_span", pa.list_(pa.int64(), 2)),
        pa.field("text", pa.string()),
        pa.field("vector", pa.list_(pa.float32(), VECTOR_DIM)),
        pa.field("sparse", pa.string()),
    ]
)


@dataclass(frozen=True)
class PageText:
    """One PDF page, 1-indexed, with the extractor's raw text."""

    page: int
    text: str


@dataclass(frozen=True)
class PyramidNode:
    """One lab vector with lineage. ``char_span`` indexes the joined source."""

    node_id: str
    pack_id: str
    grain: str
    parent_id: str
    section_id: str
    page: int
    char_span: tuple[int, int]
    text: str
    vector: list[float]
    sparse: dict[int, float]


def extract_pages(pdf_bytes: bytes) -> list[PageText]:
    """Extract text per page. Unlike production ingest, ``page`` is not discarded."""
    reader = PdfReader(io.BytesIO(pdf_bytes))
    pages: list[PageText] = []
    for index, page in enumerate(reader.pages, start=1):
        pages.append(PageText(page=index, text=page.extract_text() or ""))
    return pages


def join_pages(pages: Sequence[PageText]) -> tuple[str, tuple[tuple[int, int, int], ...]]:
    """Concatenate pages with a paragraph break. Spans are ``(page, start, end)``."""
    parts: list[str] = []
    spans: list[tuple[int, int, int]] = []
    cursor = 0
    for i, page in enumerate(pages):
        if i:
            parts.append(PAGE_JOIN)
            cursor += len(PAGE_JOIN)
        start = cursor
        parts.append(page.text)
        cursor += len(page.text)
        spans.append((page.page, start, cursor))
    return "".join(parts), tuple(spans)


def build_pyramid(
    pages: Sequence[PageText],
    pack_id: str,
    embed_fn: EmbedFn,
) -> list[PyramidNode]:
    """Segment → embed → assign lineage. Document vector is the sentence centroid."""
    _assert_pack_id(pack_id)
    if not pages:
        raise ValueError("empty page list: nothing to pyramid")
    source, page_spans = join_pages(pages)
    if not source.strip():
        raise ValueError("empty source text: nothing to pyramid")

    doc_id = _nid(pack_id, "document", 0)
    section_nodes_meta: list[dict[str, Any]] = []
    for sec_i, (page_no, start, end) in enumerate(page_spans):
        tight = _tight(source, start, end)
        if tight is None:
            continue
        section_nodes_meta.append(
            {
                "node_id": _nid(pack_id, "section", sec_i),
                "page": page_no,
                "char_span": tight,
                "text": source[tight[0] : tight[1]],
            }
        )
    if not section_nodes_meta:
        raise ValueError("empty source text: no sections")

    paragraph_metas: list[dict[str, Any]] = []
    for par_i, span in enumerate(_paragraph_spans(source)):
        page_no = _page_at(span[0], page_spans)
        section = _section_for_page(section_nodes_meta, page_no)
        paragraph_metas.append(
            {
                "node_id": _nid(pack_id, "paragraph", par_i),
                "parent_id": section["node_id"],
                "section_id": section["node_id"],
                "page": page_no,
                "char_span": span,
                "text": source[span[0] : span[1]],
            }
        )

    sentence_metas: list[dict[str, Any]] = []
    sent_i = 0
    for paragraph in paragraph_metas:
        p0, p1 = paragraph["char_span"]
        body = source[p0:p1]
        for span in _sentence_spans(body, p0):
            sentence_metas.append(
                {
                    "node_id": _nid(pack_id, "sentence", sent_i),
                    "parent_id": paragraph["node_id"],
                    "section_id": paragraph["section_id"],
                    "page": _page_at(span[0], page_spans),
                    "char_span": span,
                    "text": source[span[0] : span[1]],
                }
            )
            sent_i += 1
    if not sentence_metas:
        raise ValueError("empty source text: no sentences")

    embedded_sentences = [_embed_meta(meta, pack_id, "sentence", embed_fn) for meta in sentence_metas]
    sentence_vectors = [np.asarray(node.vector, dtype=np.float64) for node in embedded_sentences]
    sentence_sparse = [node.sparse for node in embedded_sentences]
    doc_vector = np.mean(sentence_vectors, axis=0)
    doc_sparse = _merge_sparse(sentence_sparse)
    first_page = pages[0].page

    document = PyramidNode(
        node_id=doc_id,
        pack_id=pack_id,
        grain="document",
        parent_id="",
        section_id="",
        page=first_page,
        char_span=(0, len(source)),
        text=source,
        vector=_as_vector(doc_vector),
        sparse=doc_sparse,
    )
    sections = [
        _embed_meta(
            {**meta, "parent_id": doc_id, "section_id": meta["node_id"]},
            pack_id,
            "section",
            embed_fn,
        )
        for meta in section_nodes_meta
    ]
    paragraphs = [_embed_meta(meta, pack_id, "paragraph", embed_fn) for meta in paragraph_metas]
    return [document, *sections, *paragraphs, *embedded_sentences]


def persist_pyramid(
    nodes: Sequence[PyramidNode],
    db_path: str | Path,
    *,
    replace_pack: bool = True,
) -> None:
    """Insert into ``knowledge_pyramid`` only. Never opens the ``knowledge`` table for writes."""
    if not nodes:
        raise ValueError("no pyramid nodes to persist")
    pack_id = nodes[0].pack_id
    _assert_pack_id(pack_id)
    db = lancedb.connect(str(db_path))
    names = _table_names(db)
    if PYRAMID_TABLE not in names:
        db.create_table(PYRAMID_TABLE, schema=pyramid_schema, mode="create")
    table = db.open_table(PYRAMID_TABLE)
    if replace_pack and table.count_rows() > 0:
        table.delete(f"pack_id = '{pack_id}'")
    table.add([_node_to_row(node) for node in nodes])


def load_pyramid(
    db_path: str | Path,
    pack_id: str | None = None,
) -> list[dict[str, Any]]:
    """Read lab nodes for L04. ``char_span`` is ``[start, end)``; ``sparse`` is a dict."""
    db = lancedb.connect(str(db_path))
    names = _table_names(db)
    if PYRAMID_TABLE not in names:
        return []
    table = db.open_table(PYRAMID_TABLE)
    if table.count_rows() == 0:
        return []
    rows = table.search().to_list()
    if pack_id is not None:
        _assert_pack_id(pack_id)
        rows = [row for row in rows if row.get("pack_id") == pack_id]
    return [_row_from_storage(row) for row in rows]


def ingest_pdf(
    pdf_bytes: bytes,
    pack_id: str,
    embed_fn: EmbedFn,
    db_path: str | Path,
) -> list[PyramidNode]:
    """Extract → pyramid → persist. Production ``knowledge`` is not a destination."""
    pages = extract_pages(pdf_bytes)
    nodes = build_pyramid(pages, pack_id=pack_id, embed_fn=embed_fn)
    persist_pyramid(nodes, db_path)
    return nodes


def demo_pdf_bytes(filename: str = DEMO_CORPUS_FILE) -> bytes:
    """On-disk demo PDF if present; otherwise the canonical generator text."""
    disk = Path(__file__).resolve().parents[2] / "demo_corpus" / filename
    if disk.is_file():
        return disk.read_bytes()
    module = _load_demo_corpora()
    body = module.CORPORA.get(filename)
    if body is None:
        raise KeyError(f"unknown demo corpus {filename!r}")
    return module.build_text_pdf(body)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="L03 lab: ingest a demo PDF into knowledge_pyramid")
    parser.add_argument("--corpus", choices=("automotive", "medical"), default="automotive")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH)
    args = parser.parse_args(argv)
    filename = (
        "automotive_maintenance.pdf" if args.corpus == "automotive" else "medical_hypertension.pdf"
    )
    pack_id = Path(filename).stem
    from app.modules.embedder import embedder

    nodes = ingest_pdf(demo_pdf_bytes(filename), pack_id, embedder.embed_full, args.db)
    counts: dict[str, int] = {grain: 0 for grain in ("document", "section", "paragraph", "sentence")}
    for node in nodes:
        counts[node.grain] += 1
    print(f"corpus: {filename}")
    print(f"pack_id: {pack_id}")
    print(f"table: {PYRAMID_TABLE}")
    print(f"db: {args.db}")
    print(
        "grains: document={document} section={section} paragraph={paragraph} sentence={sentence}".format(
            **counts
        )
    )
    print(f"nodes: {len(nodes)}")
    print("document vector: mean of sentence embeddings (not embed of concatenated PDF)")
    return 0


def _nid(pack_id: str, grain: str, index: int) -> str:
    return f"{pack_id}:{grain}:{index}"


def _assert_pack_id(pack_id: str) -> None:
    if not pack_id or not _PACK_ID_RE.match(pack_id):
        raise ValueError(f"invalid pack_id: {pack_id!r}")


def _tight(text: str, start: int, end: int) -> tuple[int, int] | None:
    if start >= end:
        return None
    slice_ = text[start:end]
    left = len(slice_) - len(slice_.lstrip())
    right = len(slice_.rstrip())
    if right <= left:
        return None
    return start + left, start + right


def _paragraph_spans(source: str) -> list[tuple[int, int]]:
    spans: list[tuple[int, int]] = []
    last = 0
    for match in _PARA_SPLIT.finditer(source):
        piece = _tight(source, last, match.start())
        if piece:
            spans.append(piece)
        last = match.end()
    tail = _tight(source, last, len(source))
    if tail:
        spans.append(tail)
    return spans


def _sentence_spans(paragraph: str, abs_start: int) -> list[tuple[int, int]]:
    relative: list[tuple[int, int]] = []
    last = 0
    for match in _SENTENCE_SPLIT.finditer(paragraph):
        piece = _tight(paragraph, last, match.start())
        if piece:
            relative.append(piece)
        last = match.end()
    tail = _tight(paragraph, last, len(paragraph))
    if tail:
        relative.append(tail)
    return [(abs_start + a, abs_start + b) for a, b in relative]


def _page_at(offset: int, page_spans: Sequence[tuple[int, int, int]]) -> int:
    chosen = page_spans[0][0]
    for page, start, end in page_spans:
        if offset >= start:
            chosen = page
        if start <= offset < end:
            return page
    return chosen


def _section_for_page(sections: Sequence[Mapping[str, Any]], page: int) -> Mapping[str, Any]:
    for section in sections:
        if section["page"] == page:
            return section
    return sections[-1]


def _embed_meta(
    meta: Mapping[str, Any],
    pack_id: str,
    grain: str,
    embed_fn: EmbedFn,
) -> PyramidNode:
    dense, sparse = _dense_and_sparse(embed_fn(meta["text"]))
    return PyramidNode(
        node_id=meta["node_id"],
        pack_id=pack_id,
        grain=grain,
        parent_id=str(meta.get("parent_id") or ""),
        section_id=str(meta.get("section_id") or ""),
        page=int(meta["page"]),
        char_span=(int(meta["char_span"][0]), int(meta["char_span"][1])),
        text=meta["text"],
        vector=_as_vector(dense),
        sparse=sparse,
    )


def _dense_and_sparse(output: Any) -> tuple[list[float], dict[int, float]]:
    if hasattr(output, "dense"):
        dense = list(output.dense)
        raw_sparse = getattr(output, "sparse", None) or {}
        return dense, {int(k): float(v) for k, v in dict(raw_sparse).items()}
    if isinstance(output, Mapping) and "dense" in output:
        raw_sparse = output.get("sparse") or {}
        return list(output["dense"]), {int(k): float(v) for k, v in dict(raw_sparse).items()}
    if isinstance(output, (list, tuple, np.ndarray)):
        return list(np.asarray(output, dtype=np.float32).reshape(-1)), {}
    raise TypeError(f"embed_fn returned unsupported type {type(output)!r}")


def _as_vector(values: Any) -> list[float]:
    arr = np.asarray(values, dtype=np.float32).reshape(-1)
    if arr.size != VECTOR_DIM:
        raise ValueError(f"expected {VECTOR_DIM}D vector, got {arr.size}")
    return arr.tolist()


def _merge_sparse(items: Sequence[Mapping[int, float]]) -> dict[int, float]:
    merged: dict[int, float] = {}
    for sparse in items:
        for key, value in sparse.items():
            merged[int(key)] = merged.get(int(key), 0.0) + float(value)
    return merged


def _node_to_row(node: PyramidNode) -> dict[str, Any]:
    if node.grain not in GRAINS:
        raise ValueError(f"grain {node.grain!r} not in {sorted(GRAINS)}")
    return {
        "node_id": node.node_id,
        "pack_id": node.pack_id,
        "grain": node.grain,
        "parent_id": node.parent_id,
        "section_id": node.section_id,
        "page": node.page,
        "char_span": [node.char_span[0], node.char_span[1]],
        "text": node.text,
        "vector": node.vector,
        "sparse": json.dumps({str(k): float(v) for k, v in node.sparse.items()}),
    }


def _row_from_storage(row: Mapping[str, Any]) -> dict[str, Any]:
    span = row.get("char_span") or [0, 0]
    start = int(span[0])
    end = int(span[1])
    raw_sparse = row.get("sparse")
    sparse: dict[int, float] = {}
    if isinstance(raw_sparse, dict):
        sparse = {int(k): float(v) for k, v in raw_sparse.items()}
    elif isinstance(raw_sparse, str) and raw_sparse:
        try:
            parsed = json.loads(raw_sparse)
        except json.JSONDecodeError:
            parsed = {}
        if isinstance(parsed, dict):
            sparse = {int(k): float(v) for k, v in parsed.items()}
    return {
        "node_id": str(row["node_id"]),
        "pack_id": str(row["pack_id"]),
        "grain": str(row["grain"]),
        "parent_id": str(row.get("parent_id") or ""),
        "section_id": str(row.get("section_id") or ""),
        "page": int(row["page"]),
        "char_span": [start, end],
        "text": str(row.get("text") or ""),
        "vector": [float(x) for x in row["vector"]],
        "sparse": sparse,
    }


def _table_names(db: Any) -> list[str]:
    existing = db.list_tables()
    return existing.tables if hasattr(existing, "tables") else list(existing)


def _load_demo_corpora() -> Any:
    path = Path(__file__).resolve().parents[2] / "scripts" / "generate_demo_corpora.py"
    spec = importlib.util.spec_from_file_location("generate_demo_corpora", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load demo corpora from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


if __name__ == "__main__":
    raise SystemExit(main())
