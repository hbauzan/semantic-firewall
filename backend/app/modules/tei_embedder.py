"""TEI HTTP adapter — same ``EmbeddingOutput`` seam as in-process ST.

Production filters still see dense 1024D vectors. TEI's BGE-M3 path is dense-only
(``sparse=None``); leave ``TEI_ENABLED`` off to keep the ST sparse channel.

The compose image is pinned by digest, never ``:latest``. Digest resolved
2026-09-17 from GHCR tag ``cpu-arm64-latest`` (the numbered ``cpu-arm64-1.9``
tag does not exist; huggingface/text-embeddings-inference#900).
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.core.settings import settings
from app.modules.mlx_embedder import EmbeddingOutput

logger = logging.getLogger(__name__)

PINNED_TEI_IMAGE_DIGEST = "sha256:2614a26fcdefcd4e8b2d1265cdfb8d0144b591fe7f7e9db922a38056f7c47ca2"
PINNED_TEI_IMAGE = f"ghcr.io/huggingface/text-embeddings-inference@{PINNED_TEI_IMAGE_DIGEST}"
VECTOR_DIM = 1024


class TeiEmbedder:
    """HTTP client for a local TEI sidecar. Does not construct SentenceTransformer."""

    backend_name = "tei-http"
    device = "tei"

    def __init__(
        self,
        *,
        base_url: str,
        timeout_s: float = 5.0,
        expected_dim: int = VECTOR_DIM,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_s = float(timeout_s)
        self.expected_dim = expected_dim
        self.model = settings.embedding_model
        self._client = httpx.Client(
            base_url=self.base_url,
            timeout=self.timeout_s,
        )

    def embed(self, text: str) -> list[float]:
        return self.embed_full(text).dense

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        return [item.dense for item in self.embed_full_batch(texts)]

    def embed_full(self, text: str) -> EmbeddingOutput:
        payload = self._post_embed(text)
        dense = _as_vector(_parse_dense(payload), self.expected_dim)
        return EmbeddingOutput(dense=dense, sparse=None)

    def embed_full_batch(self, texts: list[str]) -> list[EmbeddingOutput]:
        if not texts:
            return []
        payload = self._post_embed(texts)
        rows = _parse_matrix(payload, expected_rows=len(texts))
        return [
            EmbeddingOutput(dense=_as_vector(row, self.expected_dim), sparse=None)
            for row in rows
        ]

    def close(self) -> None:
        self._client.close()

    def _post_embed(self, inputs: str | list[str]) -> Any:
        response = self._client.post("/embed", json={"inputs": inputs, "normalize": False})
        response.raise_for_status()
        return response.json()


def create_runtime_embedder() -> Any:
    """Single seam: TEI HTTP when enabled, otherwise in-process ST hybrid."""
    if settings.tei_enabled:
        logger.info("Embedding backend: TEI HTTP (%s)", settings.tei_url)
        return TeiEmbedder(
            base_url=settings.tei_url,
            timeout_s=settings.tei_timeout_s,
            expected_dim=VECTOR_DIM,
        )
    from app.modules.mlx_embedder import create_hybrid_embedder

    return create_hybrid_embedder()


def _parse_dense(payload: Any) -> list[float]:
    if isinstance(payload, list):
        if payload and isinstance(payload[0], (int, float)):
            return [float(x) for x in payload]
        if payload and isinstance(payload[0], list):
            return [float(x) for x in payload[0]]
    if isinstance(payload, dict):
        if "embeddings" in payload:
            return _parse_dense(payload["embeddings"])
        data = payload.get("data")
        if isinstance(data, list) and data:
            first = data[0]
            if isinstance(first, dict) and "embedding" in first:
                return [float(x) for x in first["embedding"]]
    raise ValueError("unexpected TEI /embed payload shape")


def _parse_matrix(payload: Any, *, expected_rows: int) -> list[list[float]]:
    if isinstance(payload, list) and payload and isinstance(payload[0], list):
        rows = [[float(x) for x in row] for row in payload]
        if len(rows) != expected_rows:
            raise ValueError(f"TEI batch size {len(rows)} != {expected_rows}")
        return rows
    if expected_rows == 1:
        return [_parse_dense(payload)]
    raise ValueError("unexpected TEI /embed batch payload shape")


def _as_vector(values: list[float], expected_dim: int) -> list[float]:
    if len(values) != expected_dim:
        raise ValueError(f"TEI returned {len(values)} dims, expected {expected_dim}")
    return values
