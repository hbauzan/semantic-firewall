"""Embedding singleton — delegates to MLX hybrid backend when available."""
import logging

from app.modules.mlx_embedder import EmbeddingOutput, create_hybrid_embedder

logger = logging.getLogger(__name__)


class Embedder:
  _instance = None

  def __new__(cls):
    if cls._instance is None:
      cls._instance = super().__new__(cls)
      cls._instance.initialize()
    return cls._instance

  def initialize(self) -> None:
    self._backend = create_hybrid_embedder()
    self.device = self._backend.device
    self.model = self._backend.model

  def embed(self, text: str) -> list[float]:
    return self._backend.embed(text)

  def embed_batch(self, texts: list[str]) -> list[list[float]]:
    return self._backend.embed_batch(texts)

  def embed_full(self, text: str) -> EmbeddingOutput:
    return self._backend.embed_full(text)


embedder = Embedder()
