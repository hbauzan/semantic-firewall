# L04 — AND multi-grano offline

> **Estado:** hecho
> **Ola:** 1
> **Spec:** [`specs/pilar-2-ingesta-fractal.md`](../specs/pilar-2-ingesta-fractal.md) § regla AND.

## Objetivo

Una función de laboratorio que, dada una oración, decide PASS solo si se cumplen las tres cláusulas del PDF: proximidad micro (nodo `sentence`), validación meso (`parent_id` alineado al contexto), overlap léxico sparse. Sin blend α que compense.

## Depende de

- L03 (nodos con linaje)
- L02 (si la proximidad micro se mide en espacio blanqueado; si L02 no está, documentá distancia en espacio crudo y dejá un seam para enchufar `whiten`)

## Desbloquea

- L07 (egreso hold usa esta regla sobre oraciones de salida)
- L11 (campaña S)

## Paralelo con

Nada crítico una vez L02+L03 cerrados. L05 puede seguir en paralelo.

## Archivos a leer

- Spec Pilar 2
- Salida de L03 (tabla lab)
- [`backend/app/core/firewall.py`](../../../backend/app/core/firewall.py) — `sparse_cosine_similarity` (reusar, no mezclar con hybrid α como único gate)

## Archivos a tocar

- Módulo p. ej. `backend/app/modules/geometry/multi_grain.py`
- Tests: `backend/tests/test_multi_grain_and.py`
- Golden set chico de oraciones: del PDF, paráfrasis on-corpus, off-topic (puede ser JSON en `backend/tests/fixtures/`)

## Fuera de alcance

- SSE / chat.py
- INLP
- Sustituir el pipeline de entrada de prod
- Hybrid cosine blend como decisión final

## Tareas

- [x] API pura: `evaluate_sentence(text, pack_id) -> {passed: bool, micro, meso, lexical, reason}`.
- [x] Micro: 1-NN sobre `grain=sentence` (umbral configurado, no hardcode mágico sin constante).
- [x] Meso: el padre del hit micro debe ser el párrafo de contexto (o el 1-NN párrafo debe ser ese `parent_id`).
- [x] Léxico: overlap sparse mínimo contra ese nodo o su padre. Umbral documentado.
- [x] AND: falla cualquiera → `passed=False` con la pata que falló.
- [x] Tests: caso que pasa las tres; caso que pasa micro y falla léxico; caso off-topic.

## Tests (TDD)

```
cd backend && uv run pytest -q tests/test_multi_grain_and.py
```

## Definición de hecho

- [x] Función AND testada, sin promedio entre patas
- [x] No hay cambio de comportamiento en `/chat` de prod
- [x] Fila L04 → `hecho`

Cerrado 2026-09-18. Micro = cosine denso (espacio blanqueado si se pasa `WhiteningModel`, crudo si `whitening=None`). Meso = 1-NN párrafo == `parent_id` del hit sentence. Léxico = `sparse_cosine_similarity` vs nodo o padre. Umbrales: `MultiGrainConfig`.

## Trampas

- No “suavices” con α. El PDF pide conjunción.
- Umbrales de lab pueden ser placeholders calibrados a ojo **si** quedan en config y el test usa fixtures, no magia dispersa.

## Prompt copiable

```
Usando dev-protocol, tomá roadmap/pilares/tickets/L04-and-multigrano-offline.md.
Leé specs/pilar-2-ingesta-fractal.md. AND micro ∩ meso ∩ léxico. No toques chat.py.
TDD, uv run. Al cerrar, marcá L04 hecho.
```
