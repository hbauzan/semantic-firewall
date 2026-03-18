import asyncio
import logging
import time
import fitz  # PyMuPDF
import uuid
from pydantic import BaseModel
from app.modules.embedder import embedder
from app.modules.storage import storage
from app.core.settings import CHUNK_SIZE, CHUNK_OVERLAP, EMBEDDING_BATCH_SIZE

logger = logging.getLogger(__name__)

TASK_TTL_SECONDS = 3600  # Completed/failed tasks are pruned after 1 hour


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

def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
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
        tasks.put(task_id, TaskStatus(task_id=task_id, status="processing", progress=10.0, message="Extracting text"))
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"

        tasks.put(task_id, TaskStatus(task_id=task_id, status="processing", progress=30.0, message="Chunking text"))

        text_chunks = chunk_text(full_text)
        total_chunks = len(text_chunks)

        start_id = storage.get_max_id() + 1
        nodes = []
        batch_size = EMBEDDING_BATCH_SIZE
        for i in range(0, total_chunks, batch_size):
            batch_chunks = text_chunks[i:i+batch_size]
            embeddings = embedder.embed_batch(batch_chunks)
            for j, emb in enumerate(embeddings):
                nodes.append({
                    "id": start_id,
                    "vector": emb,
                    "text": batch_chunks[j],
                    "metadata": json.dumps({"filename": filename, "chunk_index": i+j})
                })
                start_id += 1
            progress = 30.0 + (70.0 * min(i + batch_size, total_chunks) / total_chunks)
            tasks.put(task_id, TaskStatus(task_id=task_id, status="processing", progress=progress, message="Embedding chunks"))

        if nodes:
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


async def process_pdf_async(file_bytes: bytes, filename: str) -> str:
    task_id = str(uuid.uuid4())
    tasks.put(task_id, TaskStatus(task_id=task_id, status="pending", progress=0.0, message="Task queued"))
    tasks.prune()  # Clean up old tasks on each new upload
    asyncio.create_task(asyncio.to_thread(_process_pdf_sync, file_bytes, filename, task_id))
    return task_id


def get_task_status(task_id: str) -> TaskStatus:
    return tasks.get(task_id)
