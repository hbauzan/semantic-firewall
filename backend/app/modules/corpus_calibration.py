"""Per-corpus positive-mode threshold calibration via labeled datasets.

Uses production LanceDB vectors scoped to a single pack filename.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

import numpy as np

from app.core.firewall import SemanticFirewall
from app.core.models import ConfigState
from app.core.recommended_thresholds import build_data_driven_grids
from app.modules.embedder import embedder
from app.modules.storage import storage

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATASETS_DIR = BACKEND_DIR / "calibration" / "datasets"

ProgressCallback = Callable[[float, str], None] | None


@dataclass(frozen=True)
class SweepPoint:
    param: str
    value: float
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def fpr(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) else 0.0

    @property
    def youden(self) -> float:
        return self.recall - self.fpr


@dataclass(frozen=True)
class JointSweepPoint:
    cosine_threshold: float
    excitation_threshold: int
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def fpr(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) else 0.0

    @property
    def youden(self) -> float:
        return self.recall - self.fpr


@dataclass(frozen=True)
class TripleSweepPoint:
    cosine_threshold: float
    excitation_threshold: int
    global_noise_limit: float
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def fpr(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) else 0.0

    @property
    def youden(self) -> float:
        return self.recall - self.fpr


@dataclass(frozen=True)
class PositiveCalibrationResult:
    filename: str
    corpus_id: str
    dataset_file: str
    generation_method: str | None
    cosine_threshold: float
    excitation_threshold: int
    global_noise_limit: float
    accuracy: float
    sweep_summary: dict[str, dict]


class CalibrationError(Exception):
    """Raised when calibration cannot run for a pack."""


def list_dataset_index() -> list[dict]:
    """Load all dataset manifests keyed by corpus_file."""
    index: list[dict] = []
    if not DATASETS_DIR.is_dir():
        return index
    for path in sorted(DATASETS_DIR.glob("*.json")):
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
        data["_path"] = str(path)
        index.append(data)
    return index


def resolve_dataset_for_pack(filename: str, mode: str = "recommended") -> dict | None:
    from app.modules.dataset_generator import _fingerprint_matches

    hand_curated: dict | None = None
    auto: dict | None = None
    target_mode = (mode or "recommended").lower()

    for data in list_dataset_index():
        if data.get("corpus_file") != filename:
            continue
        path = Path(data.get("_path", ""))
        if path.name.startswith("auto_"):
            ds_mode = (data.get("coverage_mode") or "").lower()
            if ds_mode == target_mode:
                auto = data
        else:
            hand_curated = data

    if hand_curated is not None:
        return hand_curated
    if auto is not None:
        fingerprint = storage.get_pack_fingerprint(filename)
        if _fingerprint_matches(auto, fingerprint):
            return auto
    return None


def has_hand_curated_dataset(filename: str) -> bool:
    """True when a non-auto labeled dataset exists for this pack."""
    for data in list_dataset_index():
        if data.get("corpus_file") != filename:
            continue
        path = Path(data.get("_path", ""))
        if path.name.startswith("auto_"):
            continue
        return True
    return False


def calibratable_filenames() -> set[str]:
    """Filenames with hand-curated labeled datasets (informational)."""
    return {
        d["corpus_file"]
        for d in list_dataset_index()
        if d.get("corpus_file") and not Path(d.get("_path", "")).name.startswith("auto_")
    }


def _calibration_base_cfg() -> ConfigState:
    """Snapshot live firewall config; force positive mode for allowlist calibration."""
    from app.core import state as state_mod

    return state_mod.config_state.model_copy(update={"firewall_mode": "positive"})


def _effective_excitation_threshold(
    excitation_threshold: float,
    word_count: int,
    adaptive_factor: float,
) -> float:
    if word_count < 6:
        return float(excitation_threshold) * adaptive_factor
    return float(excitation_threshold)


def _measure_calibration_clause(
    clause: str,
    pack_filename: str,
    cfg_probe: ConfigState,
) -> dict[str, Any]:
    cl_vec = embedder.embed(clause)
    q = np.asarray(cl_vec, dtype=np.float64)
    word_count = len(clause.split())
    results = storage.search_nearest_for_pack(cl_vec, pack_filename, k=cfg_probe.rag_top_k)
    if not results:
        return {
            "clause_text": clause,
            "has_context": False,
            "entropy": float("nan"),
            "cosine_sim": 0.0,
            "activations": 0,
            "word_count": word_count,
        }

    c = np.asarray(results[0]["vector"], dtype=np.float64).reshape(-1)
    _, _, noise_details = SemanticFirewall.run_noise_filter(q, c, cfg_probe)
    _, _, cosine_details = SemanticFirewall.run_cosine_filter(q, c, cfg_probe)
    _, _, excitation_details = SemanticFirewall.run_excitation_filter(
        q, c, cfg_probe, word_count=word_count
    )
    return {
        "clause_text": clause,
        "has_context": True,
        "entropy": float(noise_details["entropy"]),
        "cosine_sim": float(cosine_details["cosine_sim"]),
        "activations": int(excitation_details["activations"]),
        "word_count": word_count,
    }


def _measure_calibration_dataset(
    dataset: dict,
    pack_filename: str,
    cfg_probe: ConfigState,
) -> list[dict[str, Any]]:
    """Embed once per clause; cache metrics for grid sweeps."""
    rows: list[dict[str, Any]] = []
    for q in dataset["queries"]:
        clauses = SemanticFirewall.segment(q["text"].strip())
        clause_rows = [
            _measure_calibration_clause(cl, pack_filename, cfg_probe) for cl in clauses
        ]
        rows.append({
            "id": q["id"],
            "expected": q["expected"],
            "clauses": clause_rows,
        })
    return rows


def _clause_blocked_from_cache(clause: dict[str, Any], cfg: ConfigState) -> bool:
    if not clause["has_context"]:
        return True
    if cfg.noise_enabled and clause["entropy"] < cfg.global_noise_limit:
        return True
    if cfg.cosine_enabled and clause["cosine_sim"] < cfg.cosine_threshold:
        return True
    if cfg.excitation_enabled:
        exc_th = _effective_excitation_threshold(
            cfg.excitation_threshold, clause["word_count"], cfg.adaptive_factor
        )
        if clause["activations"] < exc_th:
            return True
    return False


def _prompt_blocked_from_cache(row: dict[str, Any], cfg: ConfigState) -> bool:
    return any(_clause_blocked_from_cache(cl, cfg) for cl in row["clauses"])


def _confusion_from_cache(
    cached_rows: list[dict[str, Any]],
    cfg: ConfigState,
) -> tuple[int, int, int, int]:
    tp = fp = tn = fn = 0
    for row in cached_rows:
        blocked = _prompt_blocked_from_cache(row, cfg)
        true_block = row["expected"] == "block"
        if blocked and true_block:
            tp += 1
        elif blocked and not true_block:
            fp += 1
        elif not blocked and not true_block:
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def _evaluate_prompt_positive(
    prompt: str,
    cfg: ConfigState,
    pack_filename: str,
) -> tuple[bool, str | None]:
    clauses = SemanticFirewall.segment(prompt.strip())
    for clause in clauses:
        cl_vec = embedder.embed(clause)
        results = storage.search_nearest_for_pack(cl_vec, pack_filename, k=cfg.rag_top_k)
        if not results:
            return False, "no_context"
        db_vec = results[0]["vector"]
        q_arr = np.array(cl_vec, dtype=np.float64)
        c_arr = np.array(db_vec, dtype=np.float64)
        word_count = len(clause.split())
        result = SemanticFirewall.evaluate_clause(q_arr, c_arr, cfg, word_count)
        if not result["passed"]:
            return False, result["breach_reason"]
    return True, None


def _run_evaluation(dataset: dict, cfg: ConfigState, pack_filename: str) -> list[tuple[str, str, str, bool]]:
    rows: list[tuple[str, str, str, bool]] = []
    for q in dataset["queries"]:
        passed, _reason = _evaluate_prompt_positive(q["text"], cfg, pack_filename)
        actual = "pass" if passed else "block"
        rows.append((q["id"], q["expected"], actual, actual == q["expected"]))
    return rows


def _confusion(rows: list[tuple[str, str, str, bool]]) -> tuple[int, int, int, int]:
    tp = fp = tn = fn = 0
    for _id, expected, actual, _ok in rows:
        pred_block = actual == "block"
        true_block = expected == "block"
        if pred_block and true_block:
            tp += 1
        elif pred_block and not true_block:
            fp += 1
        elif not pred_block and not true_block:
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def _pick_joint_youden_winner(points: list[JointSweepPoint]) -> JointSweepPoint:
    """Maximize Youden; on ties prefer conservative thresholds (higher exc, then cosine)."""
    return max(
        points,
        key=lambda p: (p.youden, p.f1, -p.fn, p.excitation_threshold, p.cosine_threshold),
    )


def _pick_triple_youden_winner(points: list[TripleSweepPoint]) -> TripleSweepPoint:
    return max(
        points,
        key=lambda p: (p.youden, p.f1, -p.fn, p.excitation_threshold, p.cosine_threshold),
    )


def _sweep_thresholds_2d(
    base_cfg: ConfigState,
    cached_rows: list[dict[str, Any]],
    progress_cb: ProgressCallback = None,
    progress_start: float = 35.0,
    progress_end: float = 90.0,
    grids: dict[str, list[float]] | None = None,
) -> list[JointSweepPoint]:
    """Joint grid over cosine × excitation; noise stays at base_cfg value."""
    sweep_grids = grids or build_data_driven_grids(cached_rows)
    cos_grid = list(sweep_grids["cosine_threshold"])
    exc_grid = [int(v) for v in sweep_grids["excitation_threshold"]]
    total = len(cos_grid) * len(exc_grid)
    done = 0
    points: list[JointSweepPoint] = []

    if progress_cb:
        progress_cb(progress_start, f"2D sweep: cosine × excitation (0/{total})…")

    for cos in cos_grid:
        for exc in exc_grid:
            cfg = base_cfg.model_copy(update={
                "cosine_threshold": cos,
                "excitation_threshold": exc,
            })
            tp, fp, tn, fn = _confusion_from_cache(cached_rows, cfg)
            points.append(JointSweepPoint(
                cosine_threshold=cos,
                excitation_threshold=exc,
                tp=tp, fp=fp, tn=tn, fn=fn,
            ))
            done += 1
            if progress_cb and (done == 1 or done == total or done % 50 == 0):
                pct = progress_start + (progress_end - progress_start) * done / total
                progress_cb(pct, f"2D sweep… ({done}/{total})")
    return points


def _sweep_thresholds_3d(
    base_cfg: ConfigState,
    cached_rows: list[dict[str, Any]],
    progress_cb: ProgressCallback = None,
    progress_start: float = 35.0,
    progress_end: float = 90.0,
) -> list[TripleSweepPoint]:
    """Legacy wrapper: 2D cosine×excitation at fixed noise from base_cfg."""
    joint_points = _sweep_thresholds_2d(
        base_cfg, cached_rows, progress_cb, progress_start, progress_end,
    )
    noise = base_cfg.global_noise_limit
    return [
        TripleSweepPoint(
            cosine_threshold=p.cosine_threshold,
            excitation_threshold=p.excitation_threshold,
            global_noise_limit=noise,
            tp=p.tp, fp=p.fp, tn=p.tn, fn=p.fn,
        )
        for p in joint_points
    ]


def calibrate_positive_for_pack(
    filename: str,
    coverage_mode: str = "recommended",
    progress_cb: ProgressCallback = None,
) -> PositiveCalibrationResult:
    """Run joint 3D threshold sweep (cosine × excitation × noise); return Youden optima."""
    packs = {p["filename"] for p in storage.get_summary()}
    if filename not in packs:
        raise CalibrationError(f"Pack '{filename}' is not loaded in the corpus.")

    dataset = resolve_dataset_for_pack(filename, mode=coverage_mode)
    generation_method: str | None = None
    if dataset is None:
        from app.modules.dataset_generator import generate_dataset_for_pack

        dataset = generate_dataset_for_pack(filename, mode=coverage_mode, progress_cb=progress_cb)
        generation_method = dataset.get("generation_method")
    else:
        generation_method = dataset.get("generation_method")

    base_cfg = _calibration_base_cfg()

    if progress_cb:
        progress_cb(30.0, "Measuring clause metrics…")

    cached_rows = _measure_calibration_dataset(dataset, filename, base_cfg)

    triple_points = _sweep_thresholds_3d(
        base_cfg, cached_rows, progress_cb=progress_cb,
    )
    joint_winner = _pick_joint_youden_winner([
        JointSweepPoint(
            p.cosine_threshold, p.excitation_threshold,
            p.tp, p.fp, p.tn, p.fn,
        )
        for p in triple_points
    ])
    winner = TripleSweepPoint(
        cosine_threshold=joint_winner.cosine_threshold,
        excitation_threshold=joint_winner.excitation_threshold,
        global_noise_limit=base_cfg.global_noise_limit,
        tp=joint_winner.tp,
        fp=joint_winner.fp,
        tn=joint_winner.tn,
        fn=joint_winner.fn,
    )
    logger.info(
        "Calibration %s 2D joint: cos=%.17g exc=%d noise=%.17g (fixed) youden=%.17g",
        filename,
        winner.cosine_threshold,
        winner.excitation_threshold,
        winner.global_noise_limit,
        winner.youden,
    )

    if progress_cb:
        progress_cb(95.0, "Applying optimal thresholds…")

    sweep_summary = {
        "thresholds_2d": {
            "cosine_threshold": winner.cosine_threshold,
            "excitation_threshold": winner.excitation_threshold,
            "global_noise_limit": winner.global_noise_limit,
            "noise_swept": False,
            "f1": float(winner.f1),
            "youden": float(winner.youden),
            "grid_pairs": len(triple_points),
        },
    }

    final_cfg = base_cfg.model_copy(update={
        "cosine_threshold": winner.cosine_threshold,
        "excitation_threshold": winner.excitation_threshold,
        "global_noise_limit": winner.global_noise_limit,
    })
    eval_rows = _run_evaluation(dataset, final_cfg, filename)
    accuracy = sum(1 for *_rest, ok in eval_rows if ok) / len(eval_rows)

    return PositiveCalibrationResult(
        filename=filename,
        corpus_id=dataset["corpus_id"],
        dataset_file=Path(dataset["_path"]).name,
        generation_method=generation_method,
        cosine_threshold=winner.cosine_threshold,
        excitation_threshold=winner.excitation_threshold,
        global_noise_limit=winner.global_noise_limit,
        accuracy=accuracy,
        sweep_summary=sweep_summary,
    )
