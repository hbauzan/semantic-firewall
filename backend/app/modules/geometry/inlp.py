"""Lab INLP: forbidden-theme subspace P, energy ||Π_P(Y)||², threshold τ.

Y is already whitened (L02). This module does not call production filters.

Procedure (one INLP iteration = linear separator in whitened space):
the discriminative direction is the class-mean difference
w ∝ μ_prohibited − μ_complement (LDA with shared identity covariance).
The representation is then projected onto the orthogonal complement of w
and the step repeats up to ``rank``. If the means collapse, the leading
right singular vector of the remaining prohibited cloud is used instead.

τ is not a guessed constant. ``calibrate_tau`` sets it to the maximum
benign energy so FPR is 0 with a strict ``>`` cut, then measures recall
on the evasion half of the 100+100 static golden set.

    cd backend && uv run python -m app.modules.geometry.inlp \\
        --fixture tests/fixtures/inlp_calibration_100x100.json
"""
from __future__ import annotations

import argparse
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import numpy as np

from app.modules.geometry.whitening import WhiteningModel, load_whitening, whiten

EmbedFn = Callable[[str], Any]
ThemeLabel = Literal["benign", "evasion"]

DEFAULT_RANK = 1
DEFAULT_FIXTURE = (
    Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "inlp_calibration_100x100.json"
)
DEFAULT_ARTIFACT = Path(__file__).resolve().parents[3] / "calibration" / "geometry" / "inlp_lab.npz"


@dataclass(frozen=True)
class InlpModel:
    """Orthonormal basis of P plus the calibrated cut τ."""

    basis: np.ndarray
    tau: float
    theme: str = ""
    recall: float = 0.0
    fpr: float = 0.0
    n_benign: int = 0
    n_evasion: int = 0
    n_prohibited: int = 0
    n_complement: int = 0

    @property
    def dim(self) -> int:
        return int(self.basis.shape[0])

    @property
    def rank(self) -> int:
        return int(self.basis.shape[1])


@dataclass(frozen=True)
class CalibrationResult:
    tau: float
    fpr: float
    recall: float
    n_benign: int
    n_evasion: int


@dataclass(frozen=True)
class LabeledCase:
    id: str
    label: ThemeLabel
    text: str


@dataclass(frozen=True)
class CalibrationSet:
    theme: str
    cases: tuple[LabeledCase, ...]
    source: str = "static-golden"


def fit_inlp(
    prohibited: np.ndarray,
    complement: np.ndarray,
    *,
    rank: int = DEFAULT_RANK,
) -> np.ndarray:
    """Return orthonormal basis P of shape (dim, rank). Inputs already whitened."""
    xp = np.array(prohibited, dtype=np.float64, copy=True)
    xn = np.array(complement, dtype=np.float64, copy=True)
    if xp.ndim != 2 or xn.ndim != 2:
        raise ValueError("prohibited and complement must be 2D arrays")
    if xp.shape[0] < 1 or xn.shape[0] < 1:
        raise ValueError("need at least one vector in each class")
    if xp.shape[1] != xn.shape[1]:
        raise ValueError(f"dim mismatch: {xp.shape[1]} vs {xn.shape[1]}")
    dim = int(xp.shape[1])
    if rank < 1:
        raise ValueError("rank must be >= 1")
    if rank > dim:
        raise ValueError(f"rank {rank} exceeds dim {dim}")
    columns: list[np.ndarray] = []
    for _ in range(rank):
        w = xp.mean(axis=0) - xn.mean(axis=0)
        nrm = float(np.linalg.norm(w))
        if nrm < 1e-12:
            w = _leading_singular(xp)
            nrm = float(np.linalg.norm(w))
        if nrm < 1e-12:
            raise ValueError("cannot estimate a further INLP direction")
        w = w / nrm
        for prev in columns:
            w = w - float(np.dot(w, prev)) * prev
        nrm = float(np.linalg.norm(w))
        if nrm < 1e-12:
            raise ValueError("INLP direction collapsed into previous basis")
        w = w / nrm
        columns.append(w)
        xp = xp - np.outer(xp @ w, w)
        xn = xn - np.outer(xn @ w, w)
    basis = np.stack(columns, axis=1)
    q, _ = np.linalg.qr(basis)
    return q[:, :rank]


def projection_energy(y: np.ndarray, basis: np.ndarray) -> float:
    """||Π_P(Y)||² = ||P^T Y||² for orthonormal columns of P. Y already whitened."""
    vector = np.asarray(y, dtype=np.float64).reshape(-1)
    p = np.asarray(basis, dtype=np.float64)
    if p.ndim != 2:
        raise ValueError("basis must have shape (dim, rank)")
    if vector.size != p.shape[0]:
        raise ValueError(f"y dim {vector.size} != basis dim {p.shape[0]}")
    coeffs = p.T @ vector
    return float(np.dot(coeffs, coeffs))


def should_cut(y: np.ndarray, tau: float, *, basis: np.ndarray) -> bool:
    return projection_energy(y, basis) > float(tau)


def calibrate_tau(
    benign: np.ndarray,
    evasion: np.ndarray,
    basis: np.ndarray,
) -> CalibrationResult:
    """τ = max benign energy → 0 FPR with strict >; recall on the evasion half."""
    benign_m = np.asarray(benign, dtype=np.float64)
    evasion_m = np.asarray(evasion, dtype=np.float64)
    if benign_m.ndim != 2 or evasion_m.ndim != 2:
        raise ValueError("benign and evasion must be 2D arrays")
    e_benign = np.array([projection_energy(row, basis) for row in benign_m])
    e_evasion = np.array([projection_energy(row, basis) for row in evasion_m])
    tau = float(np.max(e_benign)) if e_benign.size else 0.0
    fpr = float(np.mean(e_benign > tau)) if e_benign.size else 0.0
    recall = float(np.mean(e_evasion > tau)) if e_evasion.size else 0.0
    return CalibrationResult(
        tau=tau,
        fpr=fpr,
        recall=recall,
        n_benign=int(e_benign.size),
        n_evasion=int(e_evasion.size),
    )


def save_inlp(model: InlpModel, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        basis=np.asarray(model.basis, dtype=np.float64),
        tau=np.asarray(model.tau),
        theme=np.asarray(model.theme),
        recall=np.asarray(model.recall),
        fpr=np.asarray(model.fpr),
        n_benign=np.asarray(model.n_benign),
        n_evasion=np.asarray(model.n_evasion),
        n_prohibited=np.asarray(model.n_prohibited),
        n_complement=np.asarray(model.n_complement),
        rank=np.asarray(model.rank),
        dim=np.asarray(model.dim),
    )
    return path


def load_inlp(path: Path) -> InlpModel:
    with np.load(path, allow_pickle=False) as payload:
        theme_raw = payload["theme"]
        theme = str(theme_raw.item()) if theme_raw.shape == () else str(theme_raw)
        return InlpModel(
            basis=np.asarray(payload["basis"], dtype=np.float64),
            tau=float(payload["tau"]),
            theme=theme,
            recall=float(payload["recall"]),
            fpr=float(payload["fpr"]),
            n_benign=int(payload["n_benign"]),
            n_evasion=int(payload["n_evasion"]),
            n_prohibited=int(payload["n_prohibited"]),
            n_complement=int(payload["n_complement"]),
        )


def load_calibration_set(path: Path) -> CalibrationSet:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    cases: list[LabeledCase] = []
    for row in raw["cases"]:
        label = row["label"]
        if label not in ("benign", "evasion"):
            raise ValueError(f"unsupported label {label!r}; expected benign|evasion")
        cases.append(LabeledCase(id=str(row["id"]), label=label, text=str(row["text"])))
    return CalibrationSet(
        theme=str(raw.get("theme", "")),
        cases=tuple(cases),
        source=str(raw.get("source", "static-golden")),
    )


def fit_and_calibrate(
    prohibited: np.ndarray,
    complement: np.ndarray,
    benign: np.ndarray,
    evasion: np.ndarray,
    *,
    rank: int = DEFAULT_RANK,
    theme: str = "",
) -> InlpModel:
    basis = fit_inlp(prohibited, complement, rank=rank)
    calibration = calibrate_tau(benign, evasion, basis)
    return InlpModel(
        basis=basis,
        tau=calibration.tau,
        theme=theme,
        recall=calibration.recall,
        fpr=calibration.fpr,
        n_benign=calibration.n_benign,
        n_evasion=calibration.n_evasion,
        n_prohibited=int(np.asarray(prohibited).shape[0]),
        n_complement=int(np.asarray(complement).shape[0]),
    )


def _leading_singular(matrix: np.ndarray) -> np.ndarray:
    centered = matrix - matrix.mean(axis=0)
    if centered.shape[0] == 0:
        return np.zeros(matrix.shape[1], dtype=np.float64)
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    if vt.size == 0:
        return np.zeros(matrix.shape[1], dtype=np.float64)
    return np.asarray(vt[0], dtype=np.float64)


def _dense(output: Any) -> np.ndarray:
    if hasattr(output, "dense"):
        return np.asarray(output.dense, dtype=np.float64).reshape(-1)
    return np.asarray(output, dtype=np.float64).reshape(-1)


def _maybe_whiten(vector: np.ndarray, model: WhiteningModel | None) -> np.ndarray:
    if model is None:
        return np.asarray(vector, dtype=np.float64).reshape(-1)
    return whiten(vector, model)


def _embed_cases(
    cases: Sequence[LabeledCase],
    embed_fn: EmbedFn,
    whitening: WhiteningModel | None,
) -> tuple[np.ndarray, np.ndarray]:
    rows = [_maybe_whiten(_dense(embed_fn(case.text)), whitening) for case in cases]
    matrix = np.stack(rows)
    labels = np.array([case.label for case in cases])
    prohibited = matrix[labels == "evasion"]
    complement = matrix[labels == "benign"]
    return prohibited, complement


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="L06 lab: fit INLP subspace P and calibrate τ")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--output", type=Path, default=DEFAULT_ARTIFACT)
    parser.add_argument("--rank", type=int, default=DEFAULT_RANK)
    parser.add_argument("--whitening", type=Path, default=None, help="optional L02 npz; Y is whitened before INLP")
    args = parser.parse_args(argv)
    payload = load_calibration_set(args.fixture)
    from app.modules.embedder import embedder

    whitening = None if args.whitening is None else load_whitening(args.whitening)
    prohibited, complement = _embed_cases(payload.cases, embedder.embed, whitening)
    model = fit_and_calibrate(
        prohibited,
        complement,
        complement,
        prohibited,
        rank=args.rank,
        theme=payload.theme,
    )
    path = save_inlp(model, args.output)
    print(f"theme: {model.theme}")
    print(f"source: {payload.source}")
    print(f"rank: {model.rank}  dim: {model.dim}")
    print(f"tau: {model.tau:.6g}  fpr: {model.fpr:.6g}  recall: {model.recall:.6g}")
    print(f"n_benign: {model.n_benign}  n_evasion: {model.n_evasion}")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
