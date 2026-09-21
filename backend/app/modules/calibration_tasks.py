"""Async calibration task runner with progress tracking."""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from typing import Any

from pydantic import BaseModel

from app.core.state import _config_lock
from app.modules.corpus_calibration import (
    CalibrationError,
    calibrate_positive_for_pack,
)
from app.modules.profiles import ProfileManager

logger = logging.getLogger(__name__)

TASK_TTL_SECONDS = 3600
MAX_CONCURRENT_CALIBRATIONS = 2

_calibration_semaphore = asyncio.Semaphore(MAX_CONCURRENT_CALIBRATIONS)
_background_tasks: set[asyncio.Task] = set()


class CalibrationTaskStatus(BaseModel):
    task_id: str
    status: str
    progress: float
    message: str
    result: dict[str, Any] | None = None


class CalibrationTaskStore:
    """In-memory calibration task tracker with TTL pruning."""

    def __init__(self, ttl: int = TASK_TTL_SECONDS):
        self._tasks: dict[str, tuple[CalibrationTaskStatus, float]] = {}
        self._ttl = ttl

    def put(self, task_id: str, status: CalibrationTaskStatus) -> None:
        self._tasks[task_id] = (status, time.monotonic())

    def get(self, task_id: str) -> CalibrationTaskStatus:
        entry = self._tasks.get(task_id)
        if entry is None:
            return CalibrationTaskStatus(
                task_id=task_id,
                status="not_found",
                progress=0.0,
                message="Task not found",
            )
        return entry[0]

    def prune(self) -> None:
        now = time.monotonic()
        expired = [
            tid for tid, (st, ts) in self._tasks.items()
            if st.status in ("completed", "failed") and (now - ts) > self._ttl
        ]
        for tid in expired:
            del self._tasks[tid]


calibration_tasks = CalibrationTaskStore()


def _run_calibration_sync(filename: str, task_id: str, coverage_mode: str = "recommended") -> dict:
    def progress_cb(progress: float, message: str) -> None:
        calibration_tasks.put(
            task_id,
            CalibrationTaskStatus(
                task_id=task_id,
                status="processing",
                progress=progress,
                message=message,
            ),
        )

    result = calibrate_positive_for_pack(filename, coverage_mode=coverage_mode, progress_cb=progress_cb)
    return {
        "status": "calibrated",
        "filename": filename,
        "corpus_id": result.corpus_id,
        "dataset": result.dataset_file,
        "generation_method": result.generation_method,
        "accuracy": float(result.accuracy),
        "sweep": result.sweep_summary,
        "cosine_threshold": result.cosine_threshold,
        "excitation_threshold": result.excitation_threshold,
        "global_noise_limit": result.global_noise_limit,
    }


async def _apply_config(payload: dict) -> dict:
    from app.core import state as state_mod

    async with _config_lock:
        current = state_mod.config_state
        new_state = current.model_copy(update={
            "firewall_mode": "positive",
            "cosine_threshold": payload["cosine_threshold"],
            "excitation_threshold": payload["excitation_threshold"],
            "global_noise_limit": payload["global_noise_limit"],
            "active_corpus_file": payload["filename"],
        })
        state_mod.config_state = new_state

    ProfileManager.save_profile("_last_used", new_state)
    payload["config"] = new_state.model_dump()
    return payload


async def _guarded_calibration(filename: str, task_id: str, coverage_mode: str = "recommended") -> None:
    try:
        async with _calibration_semaphore:
            calibration_tasks.put(
                task_id,
                CalibrationTaskStatus(
                    task_id=task_id,
                    status="processing",
                    progress=0.0,
                    message="Starting calibration…",
                ),
            )
            payload = await asyncio.to_thread(_run_calibration_sync, filename, task_id, coverage_mode)
            calibration_tasks.put(
                task_id,
                CalibrationTaskStatus(
                    task_id=task_id,
                    status="processing",
                    progress=95.0,
                    message="Applying optimal thresholds…",
                ),
            )
            payload = await _apply_config(payload)
            calibration_tasks.put(
                task_id,
                CalibrationTaskStatus(
                    task_id=task_id,
                    status="completed",
                    progress=100.0,
                    message="Calibration complete",
                    result=payload,
                ),
            )
            logger.info("Calibration complete: %s (mode=%s)", filename, coverage_mode)
    except CalibrationError as e:
        calibration_tasks.put(
            task_id,
            CalibrationTaskStatus(
                task_id=task_id,
                status="failed",
                progress=0.0,
                message=str(e),
            ),
        )
    except Exception:
        logger.exception("Calibration failed for %s", filename)
        calibration_tasks.put(
            task_id,
            CalibrationTaskStatus(
                task_id=task_id,
                status="failed",
                progress=0.0,
                message="Calibration failed",
            ),
        )


async def start_calibration_async(filename: str, coverage_mode: str = "recommended") -> str:
    task_id = str(uuid.uuid4())
    calibration_tasks.put(
        task_id,
        CalibrationTaskStatus(
            task_id=task_id,
            status="pending",
            progress=0.0,
            message="Calibration queued",
        ),
    )
    calibration_tasks.prune()

    task = asyncio.create_task(_guarded_calibration(filename, task_id, coverage_mode))
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task_id


def get_calibration_task_status(task_id: str) -> CalibrationTaskStatus:
    return calibration_tasks.get(task_id)
