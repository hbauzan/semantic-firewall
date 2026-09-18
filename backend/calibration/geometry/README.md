# Lab geometry artefacts. Regenerated, not source.

## L02 whitening

Whitening fit for the automotive demo pack:

```bash
cd backend
uv run python -m app.modules.geometry.whitening --corpus automotive
```

Writes `whitening_automotive.npz` here (`μ`, regularized `Σ`, `Σ^{-1/2}`, ridge).
The file is gitignored (1024×1024). Tests use in-memory synthetic corpora; they
do not require this artefact.

`n` from sliding windows over the demo PDF body is ≪ 1024. Ridge
(`ridge = ridge_ratio * trace(Σ)/d`, default `1e-4`) makes `Σ` invertible.
Do not treat per-axis sample variance of that tiny cloud as the population claim.

## L06 INLP + τ

Fit subspace \(P\) and calibrate \(\tau\) on the static 100+100 golden set
(`tests/fixtures/inlp_calibration_100x100.json`). Labels are theme membership
(`benign|evasion`), not a generator self-score.

```bash
cd backend
uv run python -m app.modules.geometry.inlp \
  --fixture tests/fixtures/inlp_calibration_100x100.json
```

Optional `--whitening calibration/geometry/whitening_automotive.npz` applies L02
before INLP. Writes `inlp_lab.npz` here (gitignored). Tests fit and serialize
in-memory / tmp; they do not call this CLI (it loads BGE-M3).

\(\tau\) = max benign \(\|\Pi_P(Y)\|^2\) so FPR is 0 with a strict `>` cut.

