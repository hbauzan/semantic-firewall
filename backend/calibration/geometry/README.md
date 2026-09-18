# Lab geometry artefacts (L02). Regenerated, not source.

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
