"""Lab whitening: Q' = (Q − μ) Σ^{-1/2} (ZCA). Does not touch production filters.

Σ is the empirical covariance of the corpus vectors, plus a documented ridge
so the 1024×1024 matrix stays invertible when n ≪ d (demo packs).

Fit / apply / serialize. Embedder and LanceDB are injected by callers — this
module never constructs them.

Regenerate the demo artefact (gitignored):

    cd backend && uv run python -m app.modules.geometry.whitening --corpus automotive
"""
from __future__ import annotations

import argparse
import importlib.util
import sys
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

MIN_SAMPLES = 2
VECTOR_DIM = 1024
DEFAULT_RIDGE_RATIO = 1e-4
WINDOW_CHARS = 512
WINDOW_STRIDE = 64
DEMO_CORPUS_FILE = "automotive_maintenance.pdf"
DEFAULT_ARTIFACT = (
    Path(__file__).resolve().parents[3] / "calibration" / "geometry" / "whitening_automotive.npz"
)

EmbedFn = Callable[[str], Any]


@dataclass(frozen=True)
class WhiteningModel:
    """Corpus-fitted ZCA whitening. Arrays are float64."""

    mu: np.ndarray
    sigma: np.ndarray
    sigma_inv_sqrt: np.ndarray
    ridge: float
    ridge_ratio: float
    n_samples: int
    dim: int
    corpus_id: str = ""


def dense_matrix_from_rows(
    rows: Sequence[Mapping[str, Any]],
    *,
    vector_key: str = "vector",
) -> np.ndarray:
    if not rows:
        raise ValueError("need at least one row with a dense vector")
    matrix = np.stack([np.asarray(row[vector_key], dtype=np.float64).reshape(-1) for row in rows])
    return matrix


def sliding_windows(text: str, window: int = WINDOW_CHARS, stride: int = WINDOW_STRIDE) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []
    if len(stripped) <= window:
        return [stripped]
    stops = range(0, len(stripped) - window + 1, stride)
    windows = [stripped[start : start + window] for start in stops]
    last_start = len(stripped) - window
    if windows[-1] != stripped[last_start:]:
        windows.append(stripped[last_start:])
    return windows


def load_demo_corpus_body(filename: str = DEMO_CORPUS_FILE) -> str:
    path = Path(__file__).resolve().parents[3] / "scripts" / "generate_demo_corpora.py"
    spec = importlib.util.spec_from_file_location("generate_demo_corpora", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"cannot load demo corpora script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        body = module.CORPORA[filename]
    except KeyError as exc:
        raise KeyError(f"unknown demo corpus {filename!r}") from exc
    return str(body).strip()


def demo_sliding_windows(body: str | None = None) -> list[str]:
    text = body if body is not None else load_demo_corpus_body()
    return sliding_windows(text)


def _as_dense(output: Any) -> np.ndarray:
    if hasattr(output, "dense"):
        return np.asarray(output.dense, dtype=np.float64).reshape(-1)
    return np.asarray(output, dtype=np.float64).reshape(-1)


def embed_texts(texts: Sequence[str], embed_fn: EmbedFn) -> np.ndarray:
    if not texts:
        raise ValueError("need at least one text to embed")
    return np.stack([_as_dense(embed_fn(text)) for text in texts])


def fit_whitening(
    vectors: np.ndarray,
    *,
    ridge_ratio: float = DEFAULT_RIDGE_RATIO,
    corpus_id: str = "",
) -> WhiteningModel:
    x = np.asarray(vectors, dtype=np.float64)
    if x.ndim != 2:
        raise ValueError("vectors must be a 2D array of shape (n_samples, dim)")
    n_samples, dim = x.shape
    if n_samples < MIN_SAMPLES:
        raise ValueError(f"need at least {MIN_SAMPLES} samples to estimate covariance")
    mu = x.mean(axis=0)
    centered = x - mu
    # Rowvar=False → (dim, dim). ddof=1 is the unbiased scatter used as Σ.
    sigma_emp = np.cov(centered, rowvar=False, ddof=1)
    if dim == 1:
        sigma_emp = np.atleast_2d(sigma_emp)
    mean_eig = float(np.trace(sigma_emp) / max(dim, 1))
    ridge = float(ridge_ratio) * (mean_eig + 1e-12)
    sigma = sigma_emp + ridge * np.eye(dim, dtype=np.float64)
    evals, evecs = np.linalg.eigh(sigma)
    evals = np.clip(evals, 1e-12, None)
    sigma_inv_sqrt = (evecs * (1.0 / np.sqrt(evals))) @ evecs.T
    return WhiteningModel(
        mu=mu,
        sigma=sigma,
        sigma_inv_sqrt=sigma_inv_sqrt,
        ridge=ridge,
        ridge_ratio=float(ridge_ratio),
        n_samples=int(n_samples),
        dim=int(dim),
        corpus_id=corpus_id,
    )


def whiten(query: np.ndarray, model: WhiteningModel) -> np.ndarray:
    q = np.asarray(query, dtype=np.float64)
    if q.ndim == 1:
        if q.size != model.dim:
            raise ValueError(f"query dim {q.size} != model dim {model.dim}")
        return (q - model.mu) @ model.sigma_inv_sqrt
    if q.ndim != 2 or q.shape[1] != model.dim:
        raise ValueError(f"query shape {q.shape} incompatible with dim {model.dim}")
    return (q - model.mu) @ model.sigma_inv_sqrt


def save_whitening(model: WhiteningModel, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path,
        mu=model.mu,
        sigma=model.sigma,
        sigma_inv_sqrt=model.sigma_inv_sqrt,
        ridge=np.asarray(model.ridge),
        ridge_ratio=np.asarray(model.ridge_ratio),
        n_samples=np.asarray(model.n_samples),
        dim=np.asarray(model.dim),
        corpus_id=np.asarray(model.corpus_id),
    )
    return path


def load_whitening(path: Path) -> WhiteningModel:
    with np.load(path, allow_pickle=False) as payload:
        corpus_raw = payload["corpus_id"]
        corpus_id = str(corpus_raw.item()) if corpus_raw.shape == () else str(corpus_raw)
        return WhiteningModel(
            mu=np.asarray(payload["mu"], dtype=np.float64),
            sigma=np.asarray(payload["sigma"], dtype=np.float64),
            sigma_inv_sqrt=np.asarray(payload["sigma_inv_sqrt"], dtype=np.float64),
            ridge=float(payload["ridge"]),
            ridge_ratio=float(payload["ridge_ratio"]),
            n_samples=int(payload["n_samples"]),
            dim=int(payload["dim"]),
            corpus_id=corpus_id,
        )


def fit_demo_pack(
    *,
    filename: str = DEMO_CORPUS_FILE,
    embed_fn: EmbedFn,
    ridge_ratio: float = DEFAULT_RIDGE_RATIO,
) -> tuple[WhiteningModel, list[str]]:
    windows = demo_sliding_windows(load_demo_corpus_body(filename))
    if len(windows) < MIN_SAMPLES:
        raise ValueError(f"demo corpus {filename!r} produced {len(windows)} windows")
    vectors = embed_texts(windows, embed_fn)
    model = fit_whitening(vectors, ridge_ratio=ridge_ratio, corpus_id=filename)
    return model, windows


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="L02 lab: fit ZCA whitening on a demo corpus")
    parser.add_argument("--corpus", choices=("automotive", "medical"), default="automotive")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--ridge-ratio", type=float, default=DEFAULT_RIDGE_RATIO)
    args = parser.parse_args(argv)
    filename = (
        "automotive_maintenance.pdf" if args.corpus == "automotive" else "medical_hypertension.pdf"
    )
    output = args.output or (
        Path(__file__).resolve().parents[3]
        / "calibration"
        / "geometry"
        / f"whitening_{args.corpus}.npz"
    )
    from app.modules.embedder import embedder

    model, windows = fit_demo_pack(
        filename=filename,
        embed_fn=embedder.embed,
        ridge_ratio=args.ridge_ratio,
    )
    path = save_whitening(model, output)
    whitened = whiten(embed_texts(windows, embedder.embed), model)
    axis_mean = whitened.mean(axis=0)
    axis_var = whitened.var(axis=0, ddof=1)
    print(f"corpus: {filename}")
    print(f"windows: {len(windows)} (window={WINDOW_CHARS}, stride={WINDOW_STRIDE})")
    print(f"dim: {model.dim}")
    print(f"ridge: {model.ridge:.6g} (ratio={model.ridge_ratio})")
    print(f"mean |μ'| : {np.mean(np.abs(axis_mean)):.6g}")
    print(f"median var: {float(np.median(axis_var)):.6g}")
    print(f"wrote {path}")
    if model.n_samples <= model.dim:
        print(
            "note: n ≤ d; empirical Σ is singular. Ridge makes Σ^{-1/2} defined. "
            "Unit-variance on all 1024 axes is a population claim, not guaranteed "
            "on this small demo pack.",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
