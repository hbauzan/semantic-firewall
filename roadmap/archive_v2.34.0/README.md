# Legacy Roadmap Archive (v2.34.0 Checkpoint)

> **Status:** ARCHIVED / HISTORICAL REFERENCE ONLY  
> **Archive Date:** September 20, 2026  
> **Context:** Consolidated at version `v2.34.0`. Preserved for full git history and audit trail.

---

## Contents of this Archive

1. **[`roadmap.md`](./roadmap.md)**: Original active Level 1 roadmap prior to the archive checkpoint.
2. **[`roadmap-backlog.md`](./roadmap-backlog.md)**: Original deferred backlog covering Level 1 Stages 3–9 and RAG options B/C.
3. **[`nivel-1/`](./nivel-1/)**: Detailed specifications for Level 1 Stages 1 through 9.
4. **[`pilares/`](./pilares/)**: 4-pillar architectural exploration tickets (L01–L12: whitening, fractal ingestion, TEI determinism, rompepepe bidirectional fuzzing).
5. **[`vision/`](./vision/)**: High-level vision documents for Levels 2 and 3.
6. **[`archivo/`](./archivo/)**: Historical Cursor and Gemini exploratory studies.
7. **[`README_legacy.md`](./README_legacy.md)**: The original `roadmap/README.md` index file.

---

## Why Was This Roadmap Archived?

The legacy roadmap was designed around the early hypothesis that the three heads of the firewall operated as:
1. Noise filter (vector Shannon entropy / text entropy)
2. Cosine similarity gate
3. Excitation filter (fixed flat coordinate delta tolerance <= 0.005)

Empirical benchmark runs (documented in [`benchmark-report.md`](../../benchmark-report.md) and [`conclusiones_ultimo_cambio.md`](../../conclusiones_ultimo_cambio.md)) revealed that this third filter ("la abuela") provided zero rescue over cosine and dropped overall in-domain classification accuracy from 96% down to 64%.

Subsequent theoretical breakthroughs in the sibling repository `ddi-fw` (RFC-003 and the Deletor Hypothesis) proved that:
- Coordinates in normalized 1024D embedding space live in the [-0.15, +0.15] range with E[|v_d|] ≈ 0.03125.
- Silent 4- or 5-decimal truncation conventions (`round(x, 4)`, `:.4f`, float16) were catastrophically collapsing micro-interval gaps (10^-4 to 10^-6).
- When unrounded IEEE 754 full-mantissa precision (17 digits) is enforced, **Harmonic Subspace Resonance** emerges with zero foreign contamination (solo_b == 0) and a deterministic active native coordinate band (solo_a >= tau_floor).

Consequently, this legacy roadmap was archived to make way for the revived, mathematically sound Three-Headed Architecture (Cosine Difference -> Excited Dimension Count -> High-Precision 17-digit Harmonic Resonance).
