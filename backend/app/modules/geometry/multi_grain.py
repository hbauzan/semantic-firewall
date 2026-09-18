"""Lab AND multi-grain: micro ∩ meso ∩ lexical. No α blend. Not evaluate_clause.

Micro proximity is cosine on dense vectors, optionally after L02 whitening
(``whitening=None`` → raw space, documented seam). Meso: 1-NN paragraph must
be the micro hit's ``parent_id``. Lexical: ``SemanticFirewall.sparse_cosine_similarity``
against the sentence node or its parent — not hybrid dense+sparse as the gate.

Thresholds live in ``MultiGrainConfig``. Lab placeholders, not production knobs.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from app.core.firewall import SemanticFirewall
from app.modules.geometry.whitening import WhiteningModel, whiten
from app.modules.fractal_ingest import load_pyramid

EmbedFn = Callable[[str], Any]
FailLeg = Literal["micro", "meso", "lexical"]

DEFAULT_MICRO_MIN_COSINE = 0.72
DEFAULT_LEXICAL_MIN_COSINE = 0.15


@dataclass(frozen=True)
class MultiGrainConfig:
    """Lab thresholds. Change here (or pass an instance), not as literals in the AND."""

    micro_min_cosine: float = DEFAULT_MICRO_MIN_COSINE
    lexical_min_cosine: float = DEFAULT_LEXICAL_MIN_COSINE


@dataclass(frozen=True)
class LegScore:
    passed: bool
    score: float
    threshold: float
    node_id: str | None = None


@dataclass(frozen=True)
class MultiGrainVerdict:
    passed: bool
    micro: LegScore
    meso: LegScore
    lexical: LegScore
    reason: FailLeg | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "micro": self.micro,
            "meso": self.meso,
            "lexical": self.lexical,
            "reason": self.reason,
        }


def evaluate_sentence(
    text: str,
    pack_id: str,
    *,
    embed_fn: EmbedFn,
    nodes: Sequence[Mapping[str, Any]] | None = None,
    db_path: str | Path | None = None,
    whitening: WhiteningModel | None = None,
    config: MultiGrainConfig | None = None,
) -> MultiGrainVerdict:
    """PASS iff micro AND meso AND lexical. First failing leg is ``reason``."""
    cfg = config or MultiGrainConfig()
    rows = list(nodes) if nodes is not None else load_pyramid(db_path or _default_db(), pack_id)
    pack = [row for row in rows if str(row.get("pack_id", pack_id)) == pack_id]
    sentences = [row for row in pack if row.get("grain") == "sentence"]
    paragraphs = [row for row in pack if row.get("grain") == "paragraph"]
    query = _split_embedding(embed_fn(text))

    micro_hit, micro_score = _nearest(query.dense, sentences, whitening)
    micro = LegScore(
        passed=micro_hit is not None and micro_score >= cfg.micro_min_cosine,
        score=micro_score,
        threshold=cfg.micro_min_cosine,
        node_id=None if micro_hit is None else str(micro_hit["node_id"]),
    )
    if not micro.passed:
        empty = LegScore(passed=False, score=0.0, threshold=cfg.lexical_min_cosine, node_id=None)
        meso = LegScore(passed=False, score=0.0, threshold=1.0, node_id=None)
        return MultiGrainVerdict(passed=False, micro=micro, meso=meso, lexical=empty, reason="micro")

    parent_id = str(micro_hit.get("parent_id") or "")
    para_hit, _para_score = _nearest(query.dense, paragraphs, whitening)
    meso_ok = para_hit is not None and str(para_hit.get("node_id")) == parent_id
    meso = LegScore(
        passed=meso_ok,
        score=1.0 if meso_ok else 0.0,
        threshold=1.0,
        node_id=None if para_hit is None else str(para_hit["node_id"]),
    )
    if not meso.passed:
        empty = LegScore(passed=False, score=0.0, threshold=cfg.lexical_min_cosine, node_id=micro.node_id)
        return MultiGrainVerdict(passed=False, micro=micro, meso=meso, lexical=empty, reason="meso")

    parent = next((row for row in paragraphs if str(row.get("node_id")) == parent_id), None)
    lexical_score = max(
        _sparse_cosine(query.sparse, micro_hit.get("sparse")),
        _sparse_cosine(query.sparse, None if parent is None else parent.get("sparse")),
    )
    lexical = LegScore(
        passed=lexical_score >= cfg.lexical_min_cosine,
        score=lexical_score,
        threshold=cfg.lexical_min_cosine,
        node_id=micro.node_id,
    )
    if not lexical.passed:
        return MultiGrainVerdict(passed=False, micro=micro, meso=meso, lexical=lexical, reason="lexical")
    return MultiGrainVerdict(passed=True, micro=micro, meso=meso, lexical=lexical, reason=None)


@dataclass(frozen=True)
class _QueryEmb:
    dense: np.ndarray
    sparse: dict[int, float]


def _split_embedding(output: Any) -> _QueryEmb:
    if hasattr(output, "dense"):
        dense = np.asarray(output.dense, dtype=np.float64).reshape(-1)
        raw = getattr(output, "sparse", None) or {}
        sparse = {int(k): float(v) for k, v in dict(raw).items()}
        return _QueryEmb(dense=dense, sparse=sparse)
    return _QueryEmb(dense=np.asarray(output, dtype=np.float64).reshape(-1), sparse={})


def _maybe_whiten(vector: np.ndarray, model: WhiteningModel | None) -> np.ndarray:
    if model is None:
        return np.asarray(vector, dtype=np.float64).reshape(-1)
    return whiten(np.asarray(vector, dtype=np.float64).reshape(-1), model)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0.0 or nb == 0.0:
        return 0.0
    return float(np.clip(np.dot(a, b) / (na * nb), -1.0, 1.0))


def _nearest(
    query: np.ndarray,
    candidates: Sequence[Mapping[str, Any]],
    whitening: WhiteningModel | None,
) -> tuple[Mapping[str, Any] | None, float]:
    if not candidates:
        return None, -1.0
    q = _maybe_whiten(query, whitening)
    best: Mapping[str, Any] | None = None
    best_sim = -1.0
    for row in candidates:
        sim = _cosine(q, _maybe_whiten(np.asarray(row["vector"], dtype=np.float64), whitening))
        if sim > best_sim:
            best_sim = sim
            best = row
    return best, best_sim


def _sparse_cosine(left: Mapping[int, float] | None, right: Any) -> float:
    parsed: dict[int, float] | None
    if right is None:
        parsed = None
    elif isinstance(right, Mapping):
        parsed = {int(k): float(v) for k, v in right.items()}
    else:
        parsed = None
    return SemanticFirewall.sparse_cosine_similarity(left, parsed)


def _default_db() -> Path:
    return Path(__file__).resolve().parents[2] / "lancedb_data"
