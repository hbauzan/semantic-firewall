# S02 — Hoja + corte duro

> **Estado:** pendiente
> **Ola:** 1
> **Spec:** [`../00-alcance.md`](../00-alcance.md)

## Objetivo

En `backend/sello/`, pintar `[lo, hi]` de todas las filas en las 1024 y decidir `left` / `right` / `split` / `out` solo con los ejes disjuntos. Las otras dimensiones votan; no se tiran. Sin media. Sin top-k.

## Depende de

- S01 (textos). El módulo de geometría se puede testear con matrices fake **antes** de embeber; el embed live de las almas reales cierra el ticket.

## Desbloquea

- S03 (CLI press)
- S04 (ingress usa el mismo voto)

## Paralelo con

Nada una vez S01 entregó mazos. La matemática se puede TDD en paralelo con S01 usando filas sintéticas.

## Archivos a leer

- [`backend/calibration/dimension_probe/columns.py`](../../../backend/calibration/dimension_probe/columns.py) — `column_sheet`, `disjoint_indices`, `extrema_hist`
- [`backend/calibration/dimension_probe/hard_cut.py`](../../../backend/calibration/dimension_probe/hard_cut.py) — `vote_codes`, `hard_cut_label`, `press_lock`
- [`backend/tests/test_dimension_probe_hard_cut.py`](../../../backend/tests/test_dimension_probe_hard_cut.py) — contrato: 0 disjuntas ⇒ todos `out`
- Probes 4–5: [`current-research/2026-09-dimension-probe.md`](../../../current-research/2026-09-dimension-probe.md)

## Archivos a tocar

- `backend/sello/` (p. ej. `hoja.py`, `corte.py`) — **paquete nuevo**. No convertir el probe en Sello.
- Tests: `backend/tests/test_sello_hoja.py`, `backend/tests/test_sello_corte.py`

## Fuera de alcance

- CLI de censo (S03)
- Ingress / proxy
- Importar `calibration.dimension_probe` como API pública de Sello (copiá la lección, no el acoplamiento al Prisma)
- Medias, `top_mean`, ranking
- `evaluate_clause`

## Tareas

- [ ] `hoja(left, right) -> sheet` de D filas: lo/hi, overlap, gap, delta_ext. Sin campos `mean_*`.
- [ ] `disjuntas(sheet) -> list[int]` todas las no-solape, no un top-k.
- [ ] `votar(rows, lo_l, hi_l, lo_r, hi_r) -> (n, D)` códigos `left_only|right_only|both|neither`.
- [ ] `corte_duro(codes_row, disjuntas) -> left|right|split|out`. Lista vacía ⇒ `out`.
- [ ] `press_lock` de las tres almas (o fake 3-D en tests).
- [ ] Si un par real da 0 disjuntas: **no publicar** ese candado; fallar el build de artefacto, no inventar umbral.
- [ ] Embeber las almas de S01 **una vez** con el singleton; `rows.npz` en `backend/sello/out/` (gitignored).

## Tests (TDD)

Rojo primero con matrices fake (como el probe). Verde: toda D en la hoja; 0 disjuntas ⇒ `out`; tallies suman D.

```
cd backend && uv run pytest -q tests/test_sello_hoja.py tests/test_sello_corte.py --noconftest
```

## Definición de hecho

- [ ] API de hoja/corte sin medias
- [ ] Tests fake verdes
- [ ] `rows.npz` de las tres almas (live, una corrida)
- [ ] Pares headline auditados: 0 disjuntas = no se publica
- [ ] `evaluate_clause` intacto
- [ ] Fila S02 → `hecho`

## Trampas

- No reuses `column_pair` viejo si todavía tiene `top_mean` en un checkout sucio; Sello no rankea.
- No promedies 75 filas “para resumir”.
- Un segundo `SentenceTransformer` en el proceso está prohibido.

## Prompt copiable

```
Pack Sello, ticket S02. Leé roadmap/sello/00-alcance.md.
Hoja 1024 + corte duro en backend/sello/. Reusa la lección de dimension_probe, no el paquete.
Sin medias. Sin evaluate_clause. TDD. --noconftest.
Al cerrar, marcá S02 hecho en roadmap/sello/README.md.
```
