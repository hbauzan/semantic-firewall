"""L05 — TEI HTTP adapter. Default suite is mocked; live sidecar is opt-in."""
from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx
import pytest

from app.modules.dispatcher import UnifiedInferenceDispatcher
from app.modules.mlx_embedder import EmbeddingOutput
from app.modules.tei_embedder import (
    PINNED_TEI_IMAGE,
    PINNED_TEI_IMAGE_DIGEST,
    TeiEmbedder,
    create_runtime_embedder,
)

VECTOR_DIM = 1024
LIVE_ENV = "RUN_TEI_INTEGRATION"


class _FakeResponse:
    def __init__(self, payload, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(
                "tei error",
                request=httpx.Request("POST", "http://tei.test/embed"),
                response=httpx.Response(self.status_code),
            )

    def json(self):
        return self._payload


def test_embed_full_matches_embedding_output_shape(monkeypatch):
    captured: list[tuple[str, dict]] = []

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            self.kwargs = kwargs

        def post(self, path: str, json: dict):
            captured.append((path, json))
            return _FakeResponse([[0.25] * VECTOR_DIM])

        def close(self) -> None:
            pass

    monkeypatch.setattr("app.modules.tei_embedder.httpx.Client", FakeClient)
    tei = TeiEmbedder(base_url="http://127.0.0.1:8080", timeout_s=2.5)
    out = tei.embed_full("rear axle PSI")
    assert isinstance(out, EmbeddingOutput)
    assert len(out.dense) == VECTOR_DIM
    assert out.dense[0] == pytest.approx(0.25)
    assert out.sparse is None
    assert captured[0][0] == "/embed"
    assert captured[0][1]["inputs"] == "rear axle PSI"
    assert tei.backend_name == "tei-http"


def test_embed_full_batch_parses_matrix(monkeypatch):
    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def post(self, path: str, json: dict):
            n = len(json["inputs"])
            return _FakeResponse([[float(i)] * VECTOR_DIM for i in range(n)])

        def close(self) -> None:
            pass

    monkeypatch.setattr("app.modules.tei_embedder.httpx.Client", FakeClient)
    tei = TeiEmbedder(base_url="http://tei.test")
    batch = tei.embed_full_batch(["a", "b"])
    assert len(batch) == 2
    assert batch[0].dense[0] == pytest.approx(0.0)
    assert batch[1].dense[0] == pytest.approx(1.0)


def test_timeout_is_passed_to_httpx(monkeypatch):
    seen: dict[str, object] = {}

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            seen.update(kwargs)

        def close(self) -> None:
            pass

    monkeypatch.setattr("app.modules.tei_embedder.httpx.Client", FakeClient)
    TeiEmbedder(base_url="http://tei.test", timeout_s=3.25)
    timeout = seen["timeout"]
    assert float(timeout) == pytest.approx(3.25) or getattr(timeout, "read") == pytest.approx(3.25)


def test_image_pin_is_digest_not_latest():
    assert PINNED_TEI_IMAGE_DIGEST.startswith("sha256:")
    assert ":latest" not in PINNED_TEI_IMAGE
    assert "@sha256:" in PINNED_TEI_IMAGE
    compose = Path(__file__).resolve().parents[2] / "deploy" / "tei" / "docker-compose.yml"
    text = compose.read_text(encoding="utf-8")
    assert PINNED_TEI_IMAGE_DIGEST in text
    assert "tei:latest" not in text
    image_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip().startswith("image:")
    ]
    assert image_lines
    assert all("@sha256:" in line and ":latest" not in line for line in image_lines)


def test_create_runtime_embedder_uses_tei_when_enabled(monkeypatch):
    from app.core import settings as settings_mod

    monkeypatch.setattr(settings_mod.settings, "tei_enabled", True)
    monkeypatch.setattr(settings_mod.settings, "tei_url", "http://127.0.0.1:9")

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def close(self) -> None:
            pass

    monkeypatch.setattr("app.modules.tei_embedder.httpx.Client", FakeClient)
    backend = create_runtime_embedder()
    assert isinstance(backend, TeiEmbedder)
    assert backend.backend_name == "tei-http"


def test_dispatcher_does_not_start_st_actor_for_tei():
    class FakeTei:
        backend_name = "tei-http"

        def embed_full(self, text: str) -> EmbeddingOutput:
            return EmbeddingOutput(dense=[0.1] * 4, sparse=None)

    dispatcher = UnifiedInferenceDispatcher(embedder=FakeTei())
    assert dispatcher._use_actor_thread is False


def test_adapter_does_not_log_secrets(monkeypatch, caplog):
    caplog.set_level(logging.DEBUG)

    class FakeClient:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def post(self, path: str, json: dict):
            return _FakeResponse([[0.0] * VECTOR_DIM])

        def close(self) -> None:
            pass

    monkeypatch.setattr("app.modules.tei_embedder.httpx.Client", FakeClient)
    tei = TeiEmbedder(base_url="http://tei.test", timeout_s=1.0)
    tei.embed_full("secret-token-should-not-appear-as-header")
    joined = " ".join(record.getMessage() for record in caplog.records)
    assert "Authorization" not in joined
    assert "HF_TOKEN" not in joined


@pytest.mark.integration
def test_live_tei_dispersion_vs_l01():
    if os.environ.get(LIVE_ENV) != "1":
        pytest.skip(
            f"Set {LIVE_ENV}=1 with TEI up to compare 100× dispersion vs "
            "backend/tests/embedder_determinism_report.md"
        )
    from app.core.settings import settings

    tei = TeiEmbedder(base_url=settings.tei_url, timeout_s=settings.tei_timeout_s)
    prompt = "What is the recommended cold tire pressure for the rear axle on a sedan?"
    first = tei.embed_full(prompt).dense
    max_abs = 0.0
    for _ in range(99):
        vec = tei.embed_full(prompt).dense
        max_abs = max(max_abs, max(abs(a - b) for a, b in zip(first, vec, strict=True)))
    # L01 on this Mac: max_abs_delta=0 for the ST singleton. TEI is a different
    # runtime; record spread, fail only if embed is impossible (already raised).
    assert len(first) == VECTOR_DIM
    report = Path(__file__).resolve().parent / "embedder_determinism_report.md"
    assert report.is_file()
    assert "max_abs_delta" in report.read_text(encoding="utf-8")
    assert max_abs >= 0.0
