"""Corpus Endpoints — PDF upload, task status, pack management.

Extracted from routes.py as part of Router Decomposition (Finding A1).
"""
import os
import re
import logging
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.modules.ingestor import process_pdf_async, get_task_status
from app.modules.storage import storage
from app.core.settings import settings

logger = logging.getLogger(__name__)

# --- Upload constraints ---
_PDF_MAGIC = b"%PDF"
_SAFE_FILENAME_RE = re.compile(r'^[\w\s.\-()]+\.pdf$', re.UNICODE | re.IGNORECASE)

# --- Shared Dependencies ---
from app.api.endpoints._shared import verify_api_key, limiter

router = APIRouter()

# --- Corpus Endpoints ---

@router.post("/corpus/upload-pdf", dependencies=[Depends(verify_api_key)])
@limiter.limit(settings.rate_limit_upload)
async def upload_pdf(request: Request, file: UploadFile = File(...)):
    # --- File size guard: read in chunks to reject oversized payloads early ---
    chunks: list[bytes] = []
    total = 0
    limit = settings.max_upload_bytes
    while True:
        chunk = await file.read(1024 * 256)  # 256 KB per read
        if not chunk:
            break
        total += len(chunk)
        if total > limit:
            raise HTTPException(status_code=413, detail=f"File exceeds {settings.max_upload_mb} MB limit")
        chunks.append(chunk)
    file_bytes = b"".join(chunks)

    # --- PDF magic-byte validation ---
    if not file_bytes[:4].startswith(_PDF_MAGIC):
        raise HTTPException(status_code=400, detail="File is not a valid PDF")

    # --- Filename sanitization ---
    raw_name = file.filename or "upload.pdf"
    safe_name = os.path.basename(raw_name)
    if not _SAFE_FILENAME_RE.match(safe_name):
        safe_name = re.sub(r'[^\w.\-]', '_', safe_name)
        if not safe_name.lower().endswith('.pdf'):
            safe_name += '.pdf'

    task_id = await process_pdf_async(file_bytes, safe_name)
    return {"task_id": task_id}

@router.get("/corpus/task-status/{task_id}", dependencies=[Depends(verify_api_key)])
async def task_status(task_id: str):
    return get_task_status(task_id)

@router.get("/corpus/packs", dependencies=[Depends(verify_api_key)])
def list_packs():
    return {"packs": storage.get_summary()}

@router.delete("/corpus/packs/{filename}", dependencies=[Depends(verify_api_key)])
def delete_pack(filename: str):
    try:
        storage.delete_pack(filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename: contains disallowed characters")
    return {"status": "deleted", "filename": filename}
