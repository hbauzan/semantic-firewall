# L02 — Blanqueamiento offline

> **Estado:** hecho
> **Ola:** 1
> **Spec:** [`specs/pilar-1-geometria.md`](../specs/pilar-1-geometria.md)

## Objetivo

Estimar \(\mu\) y \(\Sigma\) sobre vectores del corpus demo, aplicar \(Q' = (Q-\mu)\Sigma^{-1/2}\), y dejar un módulo de laboratorio donde cada eje de \(Q'\) tiene varianza ~1. No reemplazar el filtro de producción.

## Depende de

Nada (puede leer la tabla `knowledge` existente).

## Desbloquea

- L04 (AND en espacio blanqueado o al menos con \(\mu,\Sigma\) disponibles)
- L06 (INLP sobre la misma base)

## Paralelo con

- L01, L03, L09

## Archivos a leer

- Spec Pilar 1
- [`backend/app/modules/storage.py`](../../../backend/app/modules/storage.py) — cómo se leen vectores
- [`backend/app/core/firewall.py`](../../../backend/app/core/firewall.py) — excitación actual (solo para no copiarla en crudo)
- Packs demo: `backend/demo_corpus/`

## Archivos a tocar

- Módulo nuevo de laboratorio, p. ej. `backend/app/modules/geometry/whitening.py` **o** `backend/tests/lab_whitening.py` si se quiere cero impacto en `app/` hasta promover. Preferí un módulo importable con tests, no un notebook como único artefacto.
- Tests: `backend/tests/test_whitening.py`

## Fuera de alcance

- Cambiar `run_excitation_filter` en prod
- INLP / \(\tau\) (eso es L06)
- TEI
- Ingesta multi-grano

## Tareas

- [x] Cargar vectores densos de un pack demo (automotive o medical).
- [x] Estimar \(\mu\) (1024,) y \(\Sigma\) (1024×1024). Regularizar si \(\Sigma\) es singular (ridge pequeño, documentado).
- [x] Implementar `whiten(Q, mu, Sigma) -> Q'`.
- [x] Verificar en test: media ~0, varianza por eje ~1 sobre el propio corpus (tolerancia numérica explícita).
- [x] Serializar \(\mu,\Sigma\) (o \(\Sigma^{-1/2}\)) a un artefacto de lab versionable (npy/npz), no a git LFS innecesario; documentar cómo regenerarlo.

## Tests (TDD)

Rojo: `whiten` no existe. Verde: propiedades estadísticas del corpus transformado.

```
cd backend && uv run pytest -q tests/test_whitening.py
cd backend && uv run python -m app.modules.geometry.whitening --corpus automotive
```

Módulo: [`backend/app/modules/geometry/whitening.py`](../../../backend/app/modules/geometry/whitening.py).  
Artefacto regenerable (gitignored): `backend/calibration/geometry/whitening_automotive.npz`. Cómo: [`backend/calibration/geometry/README.md`](../../../backend/calibration/geometry/README.md).

`evaluate_clause` / `run_excitation_filter` **no** se tocaron. n≪d en el demo → ridge; la propiedad var~1 por eje se testea en un corpus sintético n≫d.

## Definición de hecho

- [x] Función de blanqueamiento testada
- [x] Artefacto \(\mu,\Sigma\) regenerable con comando `uv run`
- [x] `evaluate_clause` de prod intacto
- [x] Fila L02 → `hecho`

## Trampas

- No estimés \(\Sigma\) sobre 3 vectores. Usá el pack entero.
- No inviertas \(\Sigma\) a mano si está mal condicionada; ridge y documentalo.
- Numpy/scipy vía `uv add` si hace falta, no `pip`.

## Prompt copiable

```
Usando dev-protocol, tomá roadmap/pilares/tickets/L02-blanqueamiento-offline.md.
Leé specs/pilar-1-geometria.md y 00-alcance.md.
Implementá blanqueamiento Q'=(Q-μ)Σ^{-1/2} en laboratorio. No toques el filtro de prod.
TDD, uv run. Al cerrar, marcá L02 hecho.
```
