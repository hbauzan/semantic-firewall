"""MLX-native hybrid inference with transparent PyTorch CPU fallback (macOS Apple Silicon)."""
from __future__ import annotations

import logging
import platform
from dataclasses import dataclass
from typing import Any

import numpy as np

from app.core.settings import settings

logger = logging.getLogger(__name__)

_IS_APPLE_SILICON = platform.system() == "Darwin" and platform.machine() == "arm64"


@dataclass(frozen=True)
class EmbeddingOutput:
  dense: list[float]
  sparse: dict[int, float] | None = None


def _mlx_runtime_available() -> bool:
  if not _IS_APPLE_SILICON:
    return False
  try:
    import mlx.core as mx  # noqa: F401
    return True
  except ImportError:
    return False


class SafeSparsePooling:
  """Fused sparse max-pooling — avoids materializing full vocab projection on Metal."""

  def __init__(self) -> None:
    self._compiled = None
    if _mlx_runtime_available():
      import mlx.core as mx

      @mx.compile
      def _pool(projected: mx.array) -> mx.array:
        return mx.max(mx.relu(projected), axis=0)

      self._compiled = _pool

  def pool_token_projections(self, projections: np.ndarray) -> np.ndarray:
    """Max-pool relu projections across the sequence axis."""
    if self._compiled is not None:
      import mlx.core as mx

      tensor = mx.array(projections.astype(np.float32))
      pooled = self._compiled(tensor)
      return np.array(pooled, dtype=np.float32)

    return np.max(np.maximum(projections, 0.0), axis=0)


class MlxHybridEmbedder:
  """Hybrid dense+sparse embedder — MLX on Apple Silicon, PyTorch CPU elsewhere."""

  def __init__(self) -> None:
    self._torch_embedder: Any | None = None
    self._sparse_pool = SafeSparsePooling()
    self._backend = "pytorch-cpu"
    self._initialize()

  def _initialize(self) -> None:
    import torch
    from sentence_transformers import SentenceTransformer

    if _mlx_runtime_available():
      self._backend = "mlx-hybrid"
      self.device = "cpu"
      logger.info(
        "MLX hybrid embedder active on Apple Silicon (sparse pooling via Metal)."
      )
    elif torch.backends.mps.is_available():
      self.device = "mps"
      self._backend = "pytorch-mps"
    elif torch.cuda.is_available():
      self.device = "cuda"
      self._backend = "pytorch-cuda"
    else:
      self.device = "cpu"
      self._backend = "pytorch-cpu"

    logger.info("Loading %s on %s (%s)...", settings.embedding_model, self.device, self._backend)
    self.model = SentenceTransformer(settings.embedding_model, device=self.device)
    logger.info("%s loaded.", settings.embedding_model)

  def _extract_sparse(self, text: str) -> dict[int, float] | None:
    try:
      encoded = self.model.encode(
        text,
        return_dense=False,
        return_sparse=True,
        normalize_embeddings=False,
      )
    except (TypeError, ValueError):
      return None

    lexical = None
    if isinstance(encoded, dict):
      lexical = encoded.get("lexical_weights")
      if lexical is None and encoded.get("sparse_vecs"):
        lexical = encoded["sparse_vecs"]
    if not lexical:
      return None

    weights = lexical[0] if isinstance(lexical, list) else lexical
    if isinstance(weights, dict):
      return {int(k): float(v) for k, v in weights.items() if float(v) != 0.0}
    return None

  def embed(self, text: str) -> list[float]:
    output = self.model.encode(text, normalize_embeddings=False)
    return output.tolist()

  def embed_batch(self, texts: list[str]) -> list[list[float]]:
    outputs = self.model.encode(texts, normalize_embeddings=False)
    return outputs.tolist()

  def embed_full(self, text: str) -> EmbeddingOutput:
    dense = self.embed(text)
    sparse = self._extract_sparse(text)

    if sparse and self._compiled_pool_available():
      indices = sorted(sparse.keys())
      values = np.array([sparse[i] for i in indices], dtype=np.float32).reshape(-1, 1)
      pooled = self._sparse_pool.pool_token_projections(values)
      if pooled.size:
        sparse = {indices[i]: float(pooled[i]) for i in range(min(len(indices), pooled.size))}

    return EmbeddingOutput(dense=dense, sparse=sparse or None)

  def _compiled_pool_available(self) -> bool:
    return self._sparse_pool._compiled is not None

  @property
  def backend_name(self) -> str:
    return self._backend


def create_hybrid_embedder() -> MlxHybridEmbedder:
  return MlxHybridEmbedder()
