"""L06 — INLP subspace P and τ. Does not call evaluate_clause or chat.py."""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from app.modules.geometry.inlp import (
    InlpModel,
    calibrate_tau,
    fit_inlp,
    load_calibration_set,
    load_inlp,
    projection_energy,
    save_inlp,
    should_cut,
)
from app.modules.geometry.whitening import fit_whitening, whiten

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "inlp_calibration_100x100.json"
INLP_SOURCE = Path(__file__).resolve().parents[1] / "app" / "modules" / "geometry" / "inlp.py"


def _orthonormal_basis(dim: int, rank: int, seed: int = 0) -> np.ndarray:
    rng = np.random.default_rng(seed)
    raw = rng.normal(size=(dim, rank))
    q, _ = np.linalg.qr(raw)
    return q[:, :rank]


def _cloud_in_span(basis: np.ndarray, n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    coeffs = rng.normal(size=(n, basis.shape[1]))
    return coeffs @ basis.T


def _cloud_in_complement(basis: np.ndarray, n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    dim = basis.shape[0]
    projector = np.eye(dim) - basis @ basis.T
    raw = rng.normal(size=(n, dim))
    out = raw @ projector
    norms = np.linalg.norm(out, axis=1, keepdims=True)
    return out / np.clip(norms, 1e-12, None)


def test_vector_in_p_has_high_energy():
    basis = _orthonormal_basis(dim=8, rank=1, seed=1)
    y = basis[:, 0]
    energy = projection_energy(y, basis)
    assert energy == pytest.approx(1.0, abs=1e-9)


def test_orthogonal_vector_energy_near_zero():
    basis = _orthonormal_basis(dim=8, rank=2, seed=2)
    y = _cloud_in_complement(basis, n=1, seed=9)[0]
    energy = projection_energy(y, basis)
    assert energy == pytest.approx(0.0, abs=1e-9)


def test_fit_inlp_recovers_mean_difference_direction():
    dim = 6
    prohibited = np.zeros((40, dim))
    complement = np.zeros((40, dim))
    prohibited[:, 0] = 2.0
    complement[:, 1] = 2.0
    prohibited += 0.01 * np.random.default_rng(0).normal(size=prohibited.shape)
    complement += 0.01 * np.random.default_rng(1).normal(size=complement.shape)
    basis = fit_inlp(prohibited, complement, rank=1)
    assert basis.shape == (dim, 1)
    # w should live in span{e0, e1}
    assert abs(float(basis[2:, 0].sum())) < 0.05
    aligned = abs(float(basis[:, 0] @ np.array([1.0, -1.0, 0, 0, 0, 0])))
    assert aligned > 1.2  # ~√2 if w ∥ (e0−e1)


def test_should_cut_when_energy_exceeds_tau():
    basis = _orthonormal_basis(dim=5, rank=1, seed=4)
    inside = basis[:, 0]
    outside = _cloud_in_complement(basis, n=1, seed=5)[0]
    tau = 0.25
    assert should_cut(inside, tau, basis=basis) is True
    assert should_cut(outside, tau, basis=basis) is False
    assert should_cut(inside, tau=2.0, basis=basis) is False


def test_tau_zero_fpr_max_recall_on_100_plus_100():
    basis_true = _orthonormal_basis(dim=12, rank=1, seed=11)
    complement = _cloud_in_complement(basis_true, n=120, seed=12)
    prohibited = _cloud_in_span(basis_true, n=120, seed=13) + 0.05 * _cloud_in_complement(
        basis_true, n=120, seed=14
    )
    fitted = fit_inlp(prohibited, complement, rank=1)
    benign = _cloud_in_complement(fitted, n=100, seed=20)
    evasion = 1.5 * _cloud_in_span(fitted, n=100, seed=21) + 0.02 * _cloud_in_complement(
        fitted, n=100, seed=22
    )
    calibration = calibrate_tau(benign, evasion, fitted)
    assert calibration.n_benign == 100
    assert calibration.n_evasion == 100
    assert calibration.fpr == 0.0
    assert calibration.recall == 1.0
    assert calibration.tau == pytest.approx(float(np.max([projection_energy(v, fitted) for v in benign])))
    cuts = [should_cut(v, calibration.tau, basis=fitted) for v in benign]
    assert not any(cuts)


def test_calibration_fixture_is_100_plus_100_static_labels():
    payload = load_calibration_set(FIXTURE)
    assert payload.theme
    labels = [case.label for case in payload.cases]
    assert labels.count("benign") == 100
    assert labels.count("evasion") == 100
    assert set(labels) <= {"benign", "evasion"}
    raw = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert raw["source"] == "static-golden"
    assert all(case["label"] in {"benign", "evasion"} for case in raw["cases"])


def test_calibrate_from_fixture_labels_not_explorer(tmp_path: Path):
    payload = load_calibration_set(FIXTURE)
    dim = 8
    basis_true = _orthonormal_basis(dim=dim, rank=1, seed=30)
    rng = np.random.default_rng(31)
    cache: dict[str, np.ndarray] = {}

    def embed_fn(text: str) -> np.ndarray:
        cached = cache.get(text)
        if cached is not None:
            return cached
        case = next(c for c in payload.cases if c.text == text)
        noise = 0.01 * rng.normal(size=dim)
        if case.label == "evasion":
            vector = basis_true[:, 0] + noise
        else:
            vector = _cloud_in_complement(basis_true, n=1, seed=len(cache) + 100)[0] + noise
        cache[text] = vector
        return vector

    vectors = np.stack([embed_fn(case.text) for case in payload.cases])
    prohibited = np.stack([embed_fn(c.text) for c in payload.cases if c.label == "evasion"])
    complement = np.stack([embed_fn(c.text) for c in payload.cases if c.label == "benign"])
    basis = fit_inlp(prohibited, complement, rank=1)
    benign = np.stack([vectors[i] for i, c in enumerate(payload.cases) if c.label == "benign"])
    evasion = np.stack([vectors[i] for i, c in enumerate(payload.cases) if c.label == "evasion"])
    calibration = calibrate_tau(benign, evasion, basis)
    model = InlpModel(
        basis=basis,
        tau=calibration.tau,
        theme=payload.theme,
        recall=calibration.recall,
        fpr=calibration.fpr,
        n_benign=calibration.n_benign,
        n_evasion=calibration.n_evasion,
    )
    path = save_inlp(model, tmp_path / "inlp_lab.npz")
    loaded = load_inlp(path)
    assert loaded.fpr == 0.0
    assert loaded.n_benign == 100
    assert loaded.n_evasion == 100
    assert loaded.theme == payload.theme
    assert np.allclose(loaded.basis, model.basis)


def test_roundtrip_npz(tmp_path: Path):
    basis = _orthonormal_basis(dim=7, rank=2, seed=8)
    model = InlpModel(basis=basis, tau=0.4, theme="investment_advice", recall=1.0, fpr=0.0)
    loaded = load_inlp(save_inlp(model, tmp_path / "p_tau.npz"))
    np.testing.assert_allclose(loaded.basis, basis)
    assert loaded.tau == pytest.approx(0.4)
    assert loaded.rank == 2
    assert loaded.dim == 7


def test_projection_energy_expects_already_whitened_y():
    rng = np.random.default_rng(3)
    raw = rng.normal(size=(80, 6)) * np.array([4.0, 0.2, 1.0, 1.0, 1.0, 1.0])
    raw[:, 1] = 0.9 * raw[:, 0]
    model = fit_whitening(raw)
    y_raw = raw[0]
    y_white = whiten(y_raw, model)
    basis = np.zeros((6, 1))
    basis[0, 0] = 1.0
    # Caller whitens; INLP does not call fit_whitening internally.
    assert projection_energy(y_white, basis) != pytest.approx(projection_energy(y_raw, basis))
    source = INLP_SOURCE.read_text(encoding="utf-8")
    assert "evaluate_clause" not in source
    assert "explorer" not in source.lower()
