# S04 — Ingress por cláusulas

> **Estado:** pendiente
> **Ola:** 3
> **Spec:** [`../00-alcance.md`](../00-alcance.md)

## Objetivo

Dado un prompt, partirlo en cláusulas, embeber cada una (singleton), y decidir PASS/BREACH con el sello publicado: las 1024 y el corte duro. Fail closed. Una cláusula que falla tumba el prompt.

## Depende de

- S02 (candados publicados)
- S03 (forma del censo; útil para bitácora)

## Desbloquea

- S05 (egreso llama la misma decisión sobre texto generado)
- S06 (el proxy pega acá)

## Paralelo con

S05 puede TDD el hold con un `decide()` fake si S04 ya fijó el seam.

## Archivos a leer

- [`../almas.md`](../almas.md) — piggy de prueba
- Segmentación actual del padre (solo para no copiarla ciega): cláusulas por puntuación; piggy
- [`backend/sello/`](../../../backend/sello/) de S02

## Archivos a tocar

- `backend/sello/ingress.py` (nombre exacto al implementar)
- Tests: `backend/tests/test_sello_ingress.py` — embedder **inyectado** / stub

## Fuera de alcance

- `evaluate_clause` / `firewall.py` del padre
- Egreso (S05), proxy HTTP (S06)
- Perfil chat / sentence buffer del padre
- Harm labels

## Tareas

- [ ] Partir el piggy de [`almas.md`](../almas.md) en **tres** cláusulas (python / MIT / torta).
- [ ] `decide(clause_vec, locks) -> PASS|BREACH` + bitácora (alma, votos, disjuntas).
- [ ] Política demo: modo positivo sobre almas **permitidas** configurables; vedadas opcionales. Default del demo: hay que caber en **una** alma publicada (sello de 1024) y no cortar `right`/`left` como el alma vedada del par.
- [ ] Fail closed si no hay candado publicado, embedder caído, o 0 disjuntas y la política exigía corte duro.
- [ ] Tests con vectores fake: piggy_full no es la cláusula; la mitad receta no pasa un candado python-only.

## Tests (TDD)

Sin BGE-M3 en pytest. Stub de `embed_batch`.

```
cd backend && uv run pytest -q tests/test_sello_ingress.py --noconftest
```

## Definición de hecho

- [ ] Piggy de tres cláusulas resuelto por mitad
- [ ] Bitácora por cláusula (sin media)
- [ ] Padre (`evaluate_clause`) intacto
- [ ] Fila S04 → `hecho`

## Trampas

- No juzgues la cadena entera y “después” las partes.
- No uses cosine al centroide de python.org.
- No streamees nada: S04 es decisión, no HTTP.

## Prompt copiable

```
Pack Sello, ticket S04. Leé roadmap/sello/00-alcance.md y almas.md.
Ingress por cláusulas en backend/sello/. Fail closed. Stub de embedder.
No toques evaluate_clause. TDD tests/test_sello_ingress.py --noconftest.
Al cerrar, marcá S04 hecho en roadmap/sello/README.md.
```
