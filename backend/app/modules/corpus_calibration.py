"""Per-corpus positive-mode threshold calibration via labeled datasets.

Uses production LanceDB vectors scoped to a single pack filename.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.core.firewall import SemanticFirewall
from app.core.models import ConfigState
from app.core.recommended_thresholds import POSITIVE_RECOMMENDED, SWEEP_GRIDS
from app.modules.embedder import embedder
from app.modules.storage import storage

logger = logging.getLogger(__name__)

BACKEND_DIR = Path(__file__).resolve().parents[2]
DATASETS_DIR = BACKEND_DIR / "calibration" / "datasets"


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
class PositiveCalibrationResult:
    filename: str
    corpus_id: str
    dataset_file: str
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


def resolve_dataset_for_pack(filename: str) -> dict | None:
    for data in list_dataset_index():
        if data.get("corpus_file") == filename:
            return data
    return None


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
        q_arr = np.array(cl_vec, dtype=np.float32)
        c_arr = np.array(db_vec, dtype=np.float32)
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


def _sweep_1d(
    param: str,
    values: list[float],
    base_cfg: ConfigState,
    dataset: dict,
    pack_filename: str,
) -> list[SweepPoint]:
    points: list[SweepPoint] = []
    for val in values:
        overrides: dict = {param: val}
        if param == "excitation_threshold":
            overrides[param] = int(val)
        cfg = base_cfg.model_copy(update=overrides)
        rows = _run_evaluation(dataset, cfg, pack_filename)
        tp, fp, tn, fn = _confusion(rows)
        points.append(SweepPoint(param=param, value=val, tp=tp, fp=fp, tn=tn, fn=fn))
    return points


def _pick_youden_winner(points: list[SweepPoint]) -> SweepPoint:
    return max(points, key=lambda p: (p.youden, p.f1, -p.fn))


def _pick_joint_youden_winner(points: list[JointSweepPoint]) -> JointSweepPoint:
    return max(points, key=lambda p: (p.youden, p.f1, -p.fn))


def _sweep_cosine_excitation_2d(
    base_cfg: ConfigState,
    dataset: dict,
    pack_filename: str,
    noise_fixed: float,
) -> list[JointSweepPoint]:
    """Joint grid over cosine × excitation; noise held at ``noise_fixed``."""
    points: list[JointSweepPoint] = []
    for cos in SWEEP_GRIDS["cosine_threshold"]:
        for exc in SWEEP_GRIDS["excitation_threshold"]:
            cfg = base_cfg.model_copy(update={
                "cosine_threshold": cos,
                "excitation_threshold": int(exc),
                "global_noise_limit": noise_fixed,
            })
            rows = _run_evaluation(dataset, cfg, pack_filename)
            tp, fp, tn, fn = _confusion(rows)
            points.append(JointSweepPoint(
                cosine_threshold=cos,
                excitation_threshold=int(exc),
                tp=tp, fp=fp, tn=tn, fn=fn,
            ))
    return points


def calibrate_positive_for_pack(filename: str) -> PositiveCalibrationResult:
    """Run 2D cosine×excitation sweep (noise fixed), then 1D noise; return optima."""
    packs = {p["filename"] for p in storage.get_summary()}
    if filename not in packs:
        raise CalibrationError(f"Pack '{filename}' is not loaded in the corpus.")

    dataset = resolve_dataset_for_pack(filename)
    if dataset is None:
        raise CalibrationError(
            f"No labeled calibration dataset for '{filename}'. "
            f"Known corpora: {[d.get('corpus_file') for d in list_dataset_index()]}"
        )

    base_cfg = ConfigState(firewall_mode="positive")
    noise_fixed = POSITIVE_RECOMMENDED["global_noise_limit"]

    joint_points = _sweep_cosine_excitation_2d(base_cfg, dataset, filename, noise_fixed)
    joint_winner = _pick_joint_youden_winner(joint_points)
    logger.info(
        "Calibration %s 2D cosine×excitation (noise=%.1f): cos=%.2f exc=%d youden=%.3f",
        filename, noise_fixed,
        joint_winner.cosine_threshold, joint_winner.excitation_threshold, joint_winner.youden,
    )

    held_cfg = base_cfg.model_copy(update={
        "cosine_threshold": joint_winner.cosine_threshold,
        "excitation_threshold": joint_winner.excitation_threshold,
    })
    noise_points = _sweep_1d(
        "global_noise_limit",
        SWEEP_GRIDS["global_noise_limit"],
        held_cfg,
        dataset,
        filename,
    )
    noise_winner = _pick_youden_winner(noise_points)
    logger.info(
        "Calibration %s noise 1D (cos=%.2f exc=%d): optimal=%.1f youden=%.3f",
        filename,
        joint_winner.cosine_threshold, joint_winner.excitation_threshold,
        noise_winner.value, noise_winner.youden,
    )

    sweep_summary = {
        "cosine_excitation_2d": {
            "cosine_threshold": joint_winner.cosine_threshold,
            "excitation_threshold": joint_winner.excitation_threshold,
            "noise_fixed": noise_fixed,
            "f1": round(joint_winner.f1, 4),
            "youden": round(joint_winner.youden, 4),
            "grid_pairs": len(joint_points),
        },
        "global_noise_limit_1d": {
            "optimal": noise_winner.value,
            "f1": round(noise_winner.f1, 4),
            "youden": round(noise_winner.youden, 4),
            "held_cosine": joint_winner.cosine_threshold,
            "held_excitation": joint_winner.excitation_threshold,
        },
    }

    final_cfg = base_cfg.model_copy(update={
        "cosine_threshold": joint_winner.cosine_threshold,
        "excitation_threshold": joint_winner.excitation_threshold,
        "global_noise_limit": noise_winner.value,
    })
    eval_rows = _run_evaluation(dataset, final_cfg, filename)
    accuracy = sum(1 for *_rest, ok in eval_rows if ok) / len(eval_rows)

    return PositiveCalibrationResult(
        filename=filename,
        corpus_id=dataset["corpus_id"],
        dataset_file=Path(dataset["_path"]).name,
        cosine_threshold=joint_winner.cosine_threshold,
        excitation_threshold=joint_winner.excitation_threshold,
        global_noise_limit=noise_winner.value,
        accuracy=accuracy,
        sweep_summary=sweep_summary,
    )
