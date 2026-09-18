"""Unified inference dispatcher — single-threaded GPU/MLX actor for concurrent FastAPI."""
from __future__ import annotations

import asyncio
import logging
import queue
import threading
from dataclasses import dataclass
from typing import Any

from app.modules.mlx_embedder import EmbeddingOutput
from app.modules.tei_embedder import create_runtime_embedder

logger = logging.getLogger(__name__)


@dataclass
class _InferenceTask:
  text: str
  future: asyncio.Future


class UnifiedInferenceDispatcher:
  """Serializes embedding calls — dedicated actor thread only for MLX/Metal backends."""

  def __init__(self, embedder: Any | None = None) -> None:
    self._embedder = embedder or create_runtime_embedder()
    self._queue: queue.Queue[_InferenceTask | None] = queue.Queue()
    self._thread: threading.Thread | None = None
    self._loop: asyncio.AbstractEventLoop | None = None
    self._started = False
    self._use_actor_thread = self._embedder.backend_name.startswith("st-hybrid")

  def start(self, loop: asyncio.AbstractEventLoop) -> None:
    if self._started:
      return
    self._loop = loop
    if self._use_actor_thread:
      self._thread = threading.Thread(target=self._worker, name="inference-actor", daemon=True)
      self._thread.start()
    self._started = True
    logger.info(
      "UnifiedInferenceDispatcher started (backend=%s, actor_thread=%s)",
      self._embedder.backend_name,
      self._use_actor_thread,
    )

  def stop(self) -> None:
    if not self._started:
      return
    if self._use_actor_thread and self._thread is not None:
      self._queue.put(None)
      self._thread.join(timeout=30.0)
    self._started = False
    logger.info("UnifiedInferenceDispatcher stopped.")

  async def submit_inference(self, text: str) -> EmbeddingOutput:
    if not self._started or not self._use_actor_thread:
      return await asyncio.to_thread(self._embedder.embed_full, text)

    loop = asyncio.get_running_loop()
    future: asyncio.Future[EmbeddingOutput] = loop.create_future()
    self._queue.put(_InferenceTask(text=text, future=future))
    return await future

  def _worker(self) -> None:
    while True:
      task = self._queue.get()
      if task is None:
        break
      try:
        result = self._embedder.embed_full(task.text)
        self._resolve(task.future, result)
      except Exception as exc:
        self._reject(task.future, exc)

  def _resolve(self, future: asyncio.Future, result: EmbeddingOutput) -> None:
    loop = future.get_loop()
    loop.call_soon_threadsafe(future.set_result, result)

  def _reject(self, future: asyncio.Future, exc: Exception) -> None:
    loop = future.get_loop()
    loop.call_soon_threadsafe(future.set_exception, exc)


_dispatcher: UnifiedInferenceDispatcher | None = None


def get_dispatcher() -> UnifiedInferenceDispatcher:
  global _dispatcher
  if _dispatcher is None:
    _dispatcher = UnifiedInferenceDispatcher()
  return _dispatcher
