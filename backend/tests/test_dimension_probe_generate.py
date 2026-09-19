"""Generator + envelope: fake rows only. Does not load BGE-M3."""

from __future__ import annotations

import numpy as np

from calibration.dimension_probe.generate import (
    EXPLORER_MUTATIONS,
    build_probe_rows,
    explorer_expand,
    first_clause,
    topic_from_chunk,
    _disguise_from_prisma,
    _on_corpus_from_prisma,
    _piggy_pairs,
)
from calibration.dimension_probe.metrics import (
    envelope_bounds,
    fraction_dims_inside,
    relative_slack,
    rows_inside_almost,
    rows_inside_strict,
)


def test_explorer_expand_applies_every_mutation_deterministically() -> None:
    out = explorer_expand(["hola taller"])
    assert out[0] == "hola taller"
    assert len(out) == 1 + len(EXPLORER_MUTATIONS)
    assert explorer_expand(["hola taller"]) == out
    assert any("bizcochuelo" in t for t in out)


def test_first_clause_splits_on_period() -> None:
    assert first_clause("Cambio la bombita. Hago una torta.") == "Cambio la bombita."


def test_piggy_splits_full_from_torta_clause() -> None:
    chunks = [{"text": "Presión del eje trasero en frío. Más texto del manual."}]
    triples = _piggy_pairs(chunks, limit=1)
    assert len(triples) == 1
    full, head, tail = triples[0]
    assert head.startswith("Presión")
    assert "torta" in tail.lower() or "cake" in tail.lower() or "lottery" in tail.lower() or "agujero" in tail.lower() or "system prompt" in tail.lower()
    assert head in full
    assert tail in full


def test_on_corpus_uses_prisma_topic() -> None:
    chunks = [{"text": "Las bujías de iridio requieren holgura de electrodo."}]
    texts = _on_corpus_from_prisma(chunks, limit=1)
    assert len(texts) == 1
    assert "bujías" in texts[0] or "iridio" in texts[0]


def test_disguise_wraps_same_body() -> None:
    chunks = [{"text": "Apriete la bujía a torque de taller."}]
    texts = _disguise_from_prisma(chunks, limit=1)
    assert "bujía" in texts[0].lower() or "Apriete" in texts[0]


def test_topic_from_chunk_skips_tiny_tokens() -> None:
    assert "aceite" in topic_from_chunk("el aceite del motor")


def test_build_probe_rows_has_prisma_and_piggy_families() -> None:
    chunks = [{"text": "Presión de neumáticos en frío. Más texto del Prisma."}] * 3
    rows = build_probe_rows(chunks, control_n=2, expand=False)
    groups = {g for g, _ in rows}
    assert "prisma_chunk" in groups
    assert "on_corpus" in groups
    assert "deviation" in groups
    assert "disguise" in groups
    assert "piggy_full" in groups
    assert "piggy_clause_torta" in groups
    assert sum(1 for g, _ in rows if g == "prisma_chunk") == 3


def test_envelope_marks_torta_outside_on_the_wide_axis() -> None:
    prisma = np.array([[0.0, 0.0], [1.0, 0.1], [0.5, 0.05]])
    lo, hi = envelope_bounds(prisma)
    slack = relative_slack(hi - lo, 5.0)
    on_corpus = np.array([[0.5, 0.05]])
    torta = np.array([[5.0, 0.05]])
    assert rows_inside_strict(on_corpus, lo, hi, slack) == 1.0
    assert rows_inside_strict(torta, lo, hi, slack) == 0.0
    assert float(fraction_dims_inside(torta, lo, hi, slack)[0]) < 1.0
    assert rows_inside_almost(on_corpus, lo, hi, slack) == 1.0
