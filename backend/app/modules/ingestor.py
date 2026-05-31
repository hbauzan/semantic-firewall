import asyncio
import logging
import threading
import time
import fitz  # PyMuPDF
import uuid
from pydantic import BaseModel
from app.modules.embedder import embedder
from app.modules.storage import storage
from app.core.settings import settings

logger = logging.getLogger(__name__)

TASK_TTL_SECONDS = 3600  # Completed/failed tasks are pruned after 1 hour
MAX_CONCURRENT_INGESTIONS = 3  # Limit concurrent PDF processing threads

_ingestion_semaphore = asyncio.Semaphore(MAX_CONCURRENT_INGESTIONS)
_storage_lock = threading.Lock()  # Serialize get_max_id + add_nodes to prevent ID collisions


class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str


class TaskStore:
    """In-memory task tracker with automatic TTL-based pruning."""

    def __init__(self, ttl: int = TASK_TTL_SECONDS):
        self._tasks: dict[str, tuple[TaskStatus, float]] = {}
        self._ttl = ttl

    def put(self, task_id: str, status: TaskStatus) -> None:
        self._tasks[task_id] = (status, time.monotonic())

    def get(self, task_id: str) -> TaskStatus:
        entry = self._tasks.get(task_id)
        if entry is None:
            return TaskStatus(task_id=task_id, status="not_found", progress=0.0, message="Task not found")
        return entry[0]

    def prune(self) -> None:
        """Remove terminal tasks older than TTL."""
        now = time.monotonic()
        expired = [
            tid for tid, (st, ts) in self._tasks.items()
            if st.status in ("completed", "failed") and (now - ts) > self._ttl
        ]
        for tid in expired:
            del self._tasks[tid]
        if expired:
            logger.info("Pruned %d expired tasks", len(expired))


tasks = TaskStore()

def chunk_text(text: str, chunk_size: int = settings.chunk_size, overlap: int = settings.chunk_overlap) -> list[str]:
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == text_length:
            break
        start += chunk_size - overlap
    return chunks

def _process_pdf_sync(file_bytes: bytes, filename: str, task_id: str):
    import json
    doc = None
    try:
        logger.info("Starting text extraction for %s", filename)
        tasks.put(task_id, TaskStatus(task_id=task_id, status="processing", progress=10.0, message="Extracting text"))
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"

        tasks.put(task_id, TaskStatus(task_id=task_id, status="processing", progress=30.0, message="Chunking text"))

        text_chunks = chunk_text(full_text)
        total_chunks = len(text_chunks)

        nodes = []
        batch_size = settings.embedding_batch_size
        for i in range(0, total_chunks, batch_size):
            batch_chunks = text_chunks[i:i+batch_size]
            embeddings = embedder.embed_batch(batch_chunks)
            for j, emb in enumerate(embeddings):
                nodes.append({
                    "vector": emb,
                    "text": batch_chunks[j],
                    "metadata": json.dumps({"filename": filename, "chunk_index": i+j})
                })
            progress = 30.0 + (70.0 * min(i + batch_size, total_chunks) / total_chunks)
            tasks.put(task_id, TaskStatus(task_id=task_id, status="processing", progress=progress, message="Embedding chunks"))

        if nodes:
            # Lock ensures get_max_id + add_nodes is atomic across concurrent threads
            with _storage_lock:
                start_id = storage.get_max_id() + 1
                for idx, node in enumerate(nodes):
                    node["id"] = start_id + idx
                storage.add_nodes(nodes)

        tasks.put(task_id, TaskStatus(task_id=task_id, status="completed", progress=100.0, message="Ingestion complete"))
        logger.info("Ingestion complete: %s (%d chunks)", filename, len(nodes))
    except fitz.FileDataError as e:
        logger.error("Invalid PDF '%s': %s", filename, e)
        tasks.put(task_id, TaskStatus(task_id=task_id, status="failed", progress=0.0, message="Invalid or corrupted PDF file"))
    except Exception as e:
        logger.exception("Ingestion failed for '%s'", filename)
        tasks.put(task_id, TaskStatus(task_id=task_id, status="failed", progress=0.0, message="Processing failed"))
    finally:
        if doc is not None:
            doc.close()


_background_tasks = set()

async def process_pdf_async(file_bytes: bytes, filename: str) -> str:
    task_id = str(uuid.uuid4())
    tasks.put(task_id, TaskStatus(task_id=task_id, status="pending", progress=0.0, message="Task queued"))
    tasks.prune()  # Clean up old tasks on each new upload

    async def _guarded_ingestion():
        try:
            async with _ingestion_semaphore:
                await asyncio.to_thread(_process_pdf_sync, file_bytes, filename, task_id)
        except Exception as e:
            logger.error("Guarded ingestion failed: %s", e)
            tasks.put(task_id, TaskStatus(task_id=task_id, status="failed", progress=0.0, message="Failed to process"))

    task = asyncio.create_task(_guarded_ingestion())
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task_id


def get_task_status(task_id: str) -> TaskStatus:
    return tasks.get(task_id)
