"""Head 3 — fine harmonic resonance.

Each coordinate votes once: native only (solo_a), foreign only (solo_b),
both, or neither. A foreign vote is contamination. Native mass below tau_floor
is not enough resonance. Bounds stay float32, including gaps of 5e-5.
"""
from __future__ import annotations

import numpy as np

from app.core.firewall import SemanticFirewall
from app.core.models import ConfigState
from app.modules.storage import coordinate_bounds

DIM = 1024
TAU = 15
GAP = np.float32(5e-5)


def _bands():
    native_lo = np.full(DIM, -0.05, dtype=np.float32)
    native_hi = np.full(DIM, 0.05, dtype=np.float32)
    foreign_lo = np.full(DIM, 0.20, dtype=np.float32)
    foreign_hi = np.full(DIM, 0.40, dtype=np.float32)
    return (native_lo, native_hi), (foreign_lo, foreign_hi)


def _cfg() -> ConfigState:
    return ConfigState(
        harmonic_enabled=True,
        harmonic_order=3,
        harmonic_tau_floor=TAU,
        cosine_threshold=0.0,
        excitation_threshold=0,
        global_noise_limit=0.0,
    )


def test_native_corpus_vector_passes():
    native, foreign = _bands()
    query = np.zeros(DIM, dtype=np.float32)
    passed, stage, details = SemanticFirewall.run_harmonic_resonance_filter(
        query, query, native, foreign, TAU, _cfg()
    )
    assert passed is True
    assert stage == "harmonic"
    assert details["solo_b"] == 0
    assert details["solo_a"] >= TAU
    assert details["status"] == "harmonic_resonance_validated"
    assert details["solo_a"] + details["solo_b"] + details["ambas"] + details["ninguna"] == DIM


def test_cross_domain_vector_breaches_on_foreign_band():
    native, foreign = _bands()
    query = np.zeros(DIM, dtype=np.float32)
    query[0] = np.float32(0.30)
    corpus = np.full(DIM, 0.01, dtype=np.float32)
    cfg = _cfg()
    result = SemanticFirewall.evaluate_clause(
        query,
        corpus,
        cfg,
        word_count=12,
        native_bounds=native,
        foreign_bounds=foreign,
    )
    assert result["passed"] is False
    assert result["breach_reason"] == "foreign_band_contamination"
    assert result["breach_details"]["solo_b"] > 0
    assert result["trace"][-1]["stage"] == "harmonic"


def test_ood_noise_breaches_on_insufficient_native_mass():
    native, foreign = _bands()
    query = np.full(DIM, 0.10, dtype=np.float32)
    passed, _stage, details = SemanticFirewall.run_harmonic_resonance_filter(
        query, query, native, foreign, TAU, _cfg()
    )
    assert passed is False
    assert details["solo_b"] == 0
    assert details["solo_a"] < TAU
    assert details["error"] == "insufficient_harmonic_resonance"


def test_microgap_of_5e5_does_not_collapse():
    hi_native = np.float32(0.02438219)
    lo_foreign = np.float32(hi_native + GAP)
    assert float(lo_foreign) > float(hi_native)
    assert round(float(hi_native), 4) == round(float(lo_foreign), 4)

    native_lo = np.full(DIM, -1.0, dtype=np.float32)
    native_hi = np.full(DIM, hi_native, dtype=np.float32)
    foreign_lo = np.full(DIM, lo_foreign, dtype=np.float32)
    foreign_hi = np.full(DIM, 1.0, dtype=np.float32)
    native = (native_lo, native_hi)
    foreign = (foreign_lo, foreign_hi)

    inside = np.full(DIM, hi_native, dtype=np.float32)
    outside = inside.copy()
    outside[0] = lo_foreign
    gap_point = inside.copy()
    gap_point[0] = np.float32((float(hi_native) + float(lo_foreign)) / 2.0)

    cfg = _cfg()
    native_pass, _, native_details = SemanticFirewall.run_harmonic_resonance_filter(
        inside, inside, native, foreign, TAU, cfg
    )
    foreign_pass, _, foreign_details = SemanticFirewall.run_harmonic_resonance_filter(
        outside, outside, native, foreign, TAU, cfg
    )
    gap_pass, _, gap_details = SemanticFirewall.run_harmonic_resonance_filter(
        gap_point, gap_point, native, foreign, TAU, cfg
    )
    assert native_pass is True
    assert native_details["solo_b"] == 0
    assert foreign_pass is False
    assert foreign_details["error"] == "foreign_band_contamination"
    assert foreign_details["solo_b"] == 1
    assert gap_pass is True
    assert gap_details["solo_b"] == 0
    assert gap_details["ninguna"] == 1


def test_harmonic_is_head_three():
    cfg = ConfigState()
    assert cfg.harmonic_enabled is True
    assert cfg.harmonic_order == 3
    assert cfg.harmonic_tau_floor == TAU
    pipeline = {
        name: order for order, name, _fn in SemanticFirewall.build_pipeline(cfg)
    }
    assert pipeline["harmonic"] == 3
    assert pipeline["cosine"] == 1
    assert pipeline["excitation"] == 2


def test_pack_bounds_keep_float32_extrema():
    mat = np.array(
        [
            [0.02438219, -0.10],
            [0.02443219, 0.25],
        ],
        dtype=np.float32,
    )
    lo, hi = coordinate_bounds(mat)
    assert lo.dtype == np.float32
    assert hi.dtype == np.float32
    assert lo[0] == np.min(mat[:, 0])
    assert hi[0] == np.max(mat[:, 0])
    assert float(hi[0]) > float(lo[0])
    assert round(float(lo[0]), 4) == round(float(hi[0]), 4)

    from app.modules.storage import Storage

    storage = Storage.__new__(Storage)
    storage._bounds_cache = {}
    calls = {"n": 0}

    def _vectors(_name: str) -> np.ndarray:
        calls["n"] += 1
        return mat

    storage._pack_vectors = _vectors
    first = storage.get_pack_coordinate_bounds("Prisma.pdf")
    second = storage.get_pack_coordinate_bounds("Prisma.pdf")
    assert calls["n"] == 1
    assert first[0] is second[0]
    assert first[1] is second[1]
    storage._drop_bounds_cache()
    storage.get_pack_coordinate_bounds("Prisma.pdf")
    assert calls["n"] == 2
