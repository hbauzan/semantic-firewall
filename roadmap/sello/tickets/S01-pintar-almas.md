# S01 — Pintar almas (textos + recorte)

> **Estado:** pendiente
> **Ola:** 1
> **Spec:** [`../00-alcance.md`](../00-alcance.md), [`../almas.md`](../almas.md)

## Objetivo

Dejar en disco tres mazos de texto (`python`, `legal`, `receta`) ya recortados y vetados, listos para embeber en S02. Sin llamar al embedder. Sin tocar `evaluate_clause`.

## Depende de

Nada.

## Desbloquea

- S02 (hoja + corte duro sobre vectores de estos mazos)
- S03 (press)

## Paralelo con

Nada (S02 espera estos textos).

## Archivos a leer

- [`../almas.md`](../almas.md) — fuentes, recortes, vetos
- [`backend/calibration/dimension_probe/lomo.py`](../../../backend/calibration/dimension_probe/lomo.py) — recorte por regla de texto, no umbral de embedding
- [`backend/calibration/dimension_probe/generate.py`](../../../backend/calibration/dimension_probe/generate.py) — cómo el probe arma filas (no copiar Prisma)

## Archivos a tocar

- Paquete nuevo `backend/sello/` (p. ej. `almas.py`, `classify.py`)
- Fixtures de texto bajo `backend/sello/data/` (commiteables, cortos) o generador que las escriba
- Tests: `backend/tests/test_sello_almas.py`

## Fuera de alcance

- Embeber
- Hoja / corte duro (S02)
- `evaluate_clause`, L01–L12, Prisma
- Bajar la web entera; scrapers; ToS de productos

## Tareas

- [ ] Cargar / extraer cláusulas `python` (tutorial PSF: listas, funciones, excepciones). Recortar índice, toctree, changelog.
- [ ] Cargar cláusulas `legal` desde SPDX MIT, Apache-2.0, BSD-3-Clause.
- [ ] Cargar cláusulas `receta` (reusar torta del probe + 2–3 recetas públicas del mismo grano).
- [ ] Clasificador de texto auditable: reason `python` | `legal` | `receta` | `lomo` (descartar).
- [ ] Vetos de [`almas.md`](../almas.md) con tests (ssl/exploit no entra a python; ToS scrapeado no entra a legal).
- [ ] CLI o función `build_almas()` que escriba JSON de cláusulas (sin vectores).

## Tests (TDD)

Rojo: no hay `classify` / `build_almas`. Verde: tres mazos no vacíos, lomo afuera, vetos.

```
cd backend && uv run pytest -q tests/test_sello_almas.py --noconftest
```

## Definición de hecho

- [ ] Tres mazos en disco, recortados, con `n` declarado
- [ ] Cero llamadas al embedder
- [ ] `evaluate_clause` intacto
- [ ] Fila S01 en [`../README.md`](../README.md) → `hecho`

## Trampas

- No pintes “todo el tutorial” si hay índice/toctree: eso infla el sobre.
- No uses un LLM para generar las almas.
- Un archivo SPDX = varias cláusulas, no una sola fila gigante.

## Prompt copiable

```
Pack Sello, ticket S01. Leé roadmap/sello/00-alcance.md y roadmap/sello/almas.md.
Solo textos + recorte. No embebas. No toques evaluate_clause ni L01–L12.
TDD. uv run. Tests: tests/test_sello_almas.py --noconftest.
Al cerrar, marcá S01 hecho en roadmap/sello/README.md.
```
