# Calibration datasets and harness

Versioned labeled query sets for threshold calibration and claim measurement (Nivel 1, Etapa 5).

## Datasets

| File | Corpus PDF | Domain | Queries |
|------|------------|--------|---------|
| `datasets/automotive_v1.json` | `demo_corpus/automotive_maintenance.pdf` | Automotive maintenance | 25 |
| `datasets/medical_v1.json` | `demo_corpus/medical_hypertension.pdf` | Hypertension clinical guide | 25 |

### Labels

- **on_corpus** — legitimate question about the loaded PDF domain → `expected: pass` (positive allowlist mode).
- **off_topic** — unrelated domain → `expected: block`.
- **piggybacking** — benign clause + malicious/off-topic clause → `expected: block` (segmentation claim).
- **adversarial** — jailbreak-style prompts → `expected: block`.

On-corpus queries are paraphrased questions, **not** verbatim PDF sentences (avoids retrieval leakage).

## Harness

From `backend/`:

```bash
# Evaluate / sweep (CLI — isolated temp DB + demo PDF)
uv run python tests/calibration_suite.py evaluate --dataset calibration/datasets/automotive_v1.json
uv run python tests/calibration_suite.py sweep --dataset calibration/datasets/automotive_v1.json
uv run python tests/calibration_suite.py excitation-compare --dataset calibration/datasets/automotive_v1.json
```

### In-product (positive mode)

With any pack **loaded** in LanceDB, click **Cal** next to the pack in the Control Panel. The backend auto-generates a labeled dataset when none exists (hand-curated datasets take priority).

```bash
# Starts async calibration; poll status until completed
curl -X POST http://localhost:8000/corpus/packs/my_document.pdf/calibrate-positive
curl http://localhost:8000/corpus/calibration-task-status/{task_id}
```

Applies Youden-optimal thresholds for **positive mode**:

1. **Auto dataset** (if needed) — ~25 queries: on-corpus (LLM or template fallback), off-topic/adversarial from static pools, piggybacking templates. Saved to `datasets/auto_<slug>.json`.
2. **2D joint sweep** — `cosine_threshold` × `excitation_threshold` (data-driven grid from measured metrics; noise stays at live config). Clause metrics are embedded once and cached; the grid evaluates confusion from cache only.

Evaluation uses the **live pipeline snapshot**: filter seq order (Noise/Cosine/Excitation), ON/OFF toggles, `rag_top_k`, `noise_tolerance`, and `adaptive_factor` from config at Cal time. Only the three threshold sliders are overwritten on completion.

Hand-curated datasets (`automotive_v1.json`, `medical_v1.json`) are reused without regeneration when `corpus_file` matches.

Sweep grids are centered on positive Youden defaults (`0.5315` / `150` / `4.5`) — see `app/core/recommended_thresholds.py`. HUD sliders use the same center (`frontend/src/thresholdBounds.ts`).

## Latest sweep results (v1 datasets, 3D grid 2026-07-04)

| Corpus | cosine | excitation | noise | F1 | Note |
|--------|--------|------------|-------|-----|------|
| automotive | 0.38 | 125 | 1.5 | 1.00 | prior 2D+1D run; re-run sweep CLI for 3D optima |
| medical | 0.43 | 25 | 1.5 | 1.00 | excitation at grid lower bound |

Recommended HUD defaults (slider midpoint): **0.5315 / 150 / 4.5**. Corpus **Cal** may apply different Youden optima per pack.

## Methodology notes

1. **Manual first:** datasets were hand-authored before automation.
2. **Isolated DB:** harness never touches production `lancedb_data/`.
3. **Positive mode:** evaluations use `firewall_mode=positive` unless noted.
4. **Segmentation:** multi-clause prompts use the same `SemanticFirewall.segment()` path as `/chat`.
