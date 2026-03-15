import asyncio
import fitz  # PyMuPDF
import uuid
from pydantic import BaseModel
from app.modules.embedder import embedder
from app.modules.storage import storage

class TaskStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str

tasks = {}

def chunk_text(text: str, chunk_size: int = 2048, overlap: int = 200) -> list[str]:
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
    try:
        tasks[task_id] = TaskStatus(task_id=task_id, status="processing", progress=10.0, message="Extracting text")
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        
        tasks[task_id].progress = 30.0
        tasks[task_id].message = "Chunking text"
        
        text_chunks = chunk_text(full_text)
        total_chunks = len(text_chunks)
        
        tasks[task_id].message = "Embedding chunks"
        
        start_id = storage.get_max_id() + 1
        nodes = []
        batch_size = 10
        for i in range(0, total_chunks, batch_size):
            batch_chunks = text_chunks[i:i+batch_size]
            embeddings = embedder.embed_batch(batch_chunks)
            for j, emb in enumerate(embeddings):
                import json
                nodes.append({
                    "id": start_id,
                    "vector": emb,
                    "text": batch_chunks[j],
                    "metadata": json.dumps({"filename": filename, "chunk_index": i+j})
                })
                start_id += 1
            tasks[task_id].progress = 30.0 + (70.0 * min(i + batch_size, total_chunks) / total_chunks)
        
        if nodes:
            storage.add_nodes(nodes)
            
        tasks[task_id].status = "completed"
        tasks[task_id].progress = 100.0
        tasks[task_id].message = "Ingestion complete"
    except Exception as e:
        tasks[task_id].status = "failed"
        tasks[task_id].message = str(e)

async def process_pdf_async(file_bytes: bytes, filename: str) -> str:
    task_id = str(uuid.uuid4())
    tasks[task_id] = TaskStatus(task_id=task_id, status="pending", progress=0.0, message="Task queued")
    # Dispatch to thread pool to not block main event loop
    asyncio.create_task(asyncio.to_thread(_process_pdf_sync, file_bytes, filename, task_id))
    return task_id

def get_task_status(task_id: str) -> TaskStatus:
    return tasks.get(task_id, TaskStatus(task_id=task_id, status="not_found", progress=0.0, message="Task not found"))
