"""Corpus Endpoints — PDF upload, task status, pack management.

Extracted from routes.py as part of Router Decomposition (Finding A1).
"""
import logging
import os
import re

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.modules.ingestor import process_pdf_async, get_task_status
from app.modules.storage import storage
from app.modules.corpus_calibration import (
    calibratable_filenames,
    CalibrationError,
)
from app.modules.dataset_generator import has_auto_dataset
from app.modules.calibration_tasks import (
    start_calibration_async,
    get_calibration_task_status,
)
from app.core.settings import settings

logger = logging.getLogger(__name__)

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

@router.get("/corpus/calibration-task-status/{task_id}", dependencies=[Depends(verify_api_key)])
async def calibration_task_status(task_id: str):
    status = get_calibration_task_status(task_id)
    payload = status.model_dump()
    return payload

@router.get("/corpus/packs", dependencies=[Depends(verify_api_key)])
def list_packs():
    hand_curated = calibratable_filenames()
    packs = []
    for pack in storage.get_summary():
        fname = pack["filename"]
        packs.append({
            **pack,
            "calibratable": fname in hand_curated,
            "has_auto_dataset": has_auto_dataset(fname),
        })
    return {"packs": packs, "calibratable_corpora": sorted(hand_curated)}

@router.delete("/corpus/packs/{filename}", dependencies=[Depends(verify_api_key)])
def delete_pack(filename: str):
    try:
        storage.delete_pack(filename)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid filename: contains disallowed characters")
    return {"status": "deleted", "filename": filename}


@router.post("/corpus/packs/{filename}/calibrate-positive", dependencies=[Depends(verify_api_key)])
@limiter.limit(settings.rate_limit_upload)
async def calibrate_pack_positive(request: Request, filename: str):
    """Start async Youden threshold sweep for a loaded pack."""
    packs = {p["filename"] for p in storage.get_summary()}
    if filename not in packs:
        raise HTTPException(status_code=404, detail=f"Pack '{filename}' is not loaded in the corpus.")

    try:
        task_id = await start_calibration_async(filename)
    except CalibrationError as e:
        raise HTTPException(status_code=404, detail=str(e))

    return {"task_id": task_id}
