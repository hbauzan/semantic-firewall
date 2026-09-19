# S03 — CLI press (censo por fila)

> **Estado:** pendiente
> **Ola:** 2
> **Spec:** [`../00-alcance.md`](../00-alcance.md)

## Objetivo

Un comando que lee `backend/sello/out/rows.npz` y escribe, **una ficha por fila**, el voto de las 1024 y el corte duro. Sin re-embeber. Sin medias.

## Depende de

- S02 (`press_lock` + `rows.npz`)

## Desbloquea

- Informe de calibración para S04 (qué pares se publican)
- Bitácora del mismo shape que usará ingress

## Paralelo con

Nada crítico.

## Archivos a leer

- [`backend/calibration/dimension_probe/hard_cut.py`](../../../backend/calibration/dimension_probe/hard_cut.py) — CLI que lee `rows.npz`
- Probe 5 en [`current-research/2026-09-dimension-probe.md`](../../../current-research/2026-09-dimension-probe.md)

## Archivos a tocar

- `backend/sello/` CLI (`python -m sello.press` o equivalente bajo `calibration` no)
- `backend/sello/out/press.json`, `press_*.csv`, `press_votes.npz` (gitignored)
- Tests: `backend/tests/test_sello_press.py` (fake `rows.npz` en tmp)

## Fuera de alcance

- Ingress HTTP (S04)
- Re-embeber
- Promediar `n_left_only` entre filas; el censo es conteo de labels, los extremos de tallies son lo/hi

## Tareas

- [ ] CLI: `--rows`, `--out`. Falta `rows.npz` ⇒ exit distinto de 0 con mensaje claro.
- [ ] Locks: python↔receta, python↔legal, legal↔receta.
- [ ] Por familia: `census` (left/right/split/out), `tally_extrema` lo/hi, `rows` todas.
- [ ] CSV headline (python vs receta): una línea por fila + votos de las disjuntas.
- [ ] `press_votes.npz`: matriz uint8 (n, 1024) por familia y lock.
- [ ] Si un lock tiene 0 disjuntas: declararlo en el JSON (`published: false`), no inventar ejes.

## Tests (TDD)

Fake mazos 3-D. El CLI se prueba con un `tmp_path`.

```
cd backend && uv run pytest -q tests/test_sello_press.py --noconftest
```

Live (no es CI): `cd backend && uv run python -m sello.press`

## Definición de hecho

- [ ] Tests fake verdes
- [ ] Artefacto live escrito (gitignored)
- [ ] Cero campos `mean_*` en el JSON
- [ ] Fila S03 → `hecho`

## Trampas

- No imprimas un top-5 y calles el resto.
- No uses `summary.json` del probe Prisma.

## Prompt copiable

```
Pack Sello, ticket S03. Leé roadmap/sello/00-alcance.md.
CLI press sobre rows.npz de Sello. Una ficha por fila. Sin medias. Sin re-embeber.
TDD tests/test_sello_press.py --noconftest.
Al cerrar, marcá S03 hecho en roadmap/sello/README.md.
```
