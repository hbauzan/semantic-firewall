"""PDF ingestion tests — pypdf extraction and task-status contracts."""
from __future__ import annotations

import importlib.util
from pathlib import Path

from app.modules.ingestor import _extract_pdf_text, _process_pdf_sync, tasks
from app.modules.mlx_embedder import EmbeddingOutput


def _load_demo_corpora_script():
    path = Path(__file__).resolve().parents[1] / "scripts" / "generate_demo_corpora.py"
    spec = importlib.util.spec_from_file_location("generate_demo_corpora", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _fake_embedding(_text: str) -> EmbeddingOutput:
    return EmbeddingOutput(dense=[0.0] * 1024, sparse={1: 1.0})


class _FakeStorage:
    def __init__(self) -> None:
        self.nodes: list[dict] = []

    def get_max_id(self) -> int:
        return 0

    def add_nodes(self, nodes: list[dict]) -> None:
        self.nodes = list(nodes)


def test_extract_pdf_text_roundtrip():
    demo = _load_demo_corpora_script()
    pdf_bytes = demo.build_text_pdf(demo.CORPORA["automotive_maintenance.pdf"])
    text = _extract_pdf_text(pdf_bytes)
    assert "Tire pressure monitoring" in text
    assert "OBD-II" in text


def test_process_pdf_sync_completes_with_extracted_text(monkeypatch):
    demo = _load_demo_corpora_script()
    fake_storage = _FakeStorage()
    captured: list[str] = []

    def _capture(text: str) -> EmbeddingOutput:
        captured.append(text)
        return _fake_embedding(text)

    monkeypatch.setattr("app.modules.ingestor.embedder.embed_full", _capture)
    monkeypatch.setattr("app.modules.ingestor.storage", fake_storage)

    pdf_bytes = demo.build_text_pdf("Brake pad inspection should occur every 12,000 miles.")
    _process_pdf_sync(pdf_bytes, "brakes.pdf", "task-ok")
    status = tasks.get("task-ok")
    assert status.status == "completed"
    assert status.message == "Ingestion complete"
    assert any("Brake pad inspection" in chunk for chunk in captured)
    assert fake_storage.nodes
    assert fake_storage.nodes[0]["id"] == 1


def test_process_pdf_sync_invalid_file_is_failed_not_processing_error(monkeypatch):
    monkeypatch.setattr("app.modules.ingestor.embedder.embed_full", _fake_embedding)
    monkeypatch.setattr("app.modules.ingestor.storage", _FakeStorage())

    _process_pdf_sync(b"%PDF-not-a-real-file", "corrupt.pdf", "task-bad")
    status = tasks.get("task-bad")
    assert status.status == "failed"
    assert status.message == "Invalid or corrupted PDF file"


def test_process_pdf_sync_embedder_errors_stay_processing_failed(monkeypatch):
    demo = _load_demo_corpora_script()

    def _boom(_text: str) -> EmbeddingOutput:
        raise RuntimeError("embedder down")

    monkeypatch.setattr("app.modules.ingestor.embedder.embed_full", _boom)
    monkeypatch.setattr("app.modules.ingestor.storage", _FakeStorage())

    pdf_bytes = demo.build_text_pdf("Coolant system maintenance includes thermostat testing.")
    _process_pdf_sync(pdf_bytes, "coolant.pdf", "task-embed-fail")
    status = tasks.get("task-embed-fail")
    assert status.status == "failed"
    assert status.message == "Processing failed"
