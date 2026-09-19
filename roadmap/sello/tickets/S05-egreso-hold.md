# S05 — Egreso hold

> **Estado:** pendiente
> **Ola:** 3
> **Spec:** [`../00-alcance.md`](../00-alcance.md)

## Objetivo

Retener la generación completa, partirla, y pasar **cada** oración entregable por el mismo `decide()` de S04. Cero tokens al cliente hasta el hold. No hay perfil chat en Sello.

## Depende de

- S04 (`decide` + splitter)

## Desbloquea

- S06 (el proxy no streamea crudo)

## Paralelo con

S04 si el seam `decide=` ya existe.

## Archivos a leer

- [`../00-alcance.md`](../00-alcance.md) — “Hold solamente en la hija”
- Egreso del padre (L07/L08) **solo como anti-patrón**: el perfil `chat` puede soltar media frase; Sello no lo copia.
- Oracle: se puntúa texto **entregado**, no un flag interno.

## Archivos a tocar

- `backend/sello/egreso.py`
- Tests: `backend/tests/test_sello_egreso.py`

## Fuera de alcance

- Sentence buffer estilo chat
- DLP / PAN / homoglifos (otra cabeza; no es este ticket)
- INLP
- Cablear `egress_profile` del padre
- HTTP (S06)

## Tareas

- [ ] `hold(tokens_or_text, decide=...) -> delivered | block`.
- [ ] Nada se emite antes de `decide` sobre las cláusulas del texto acumulado.
- [ ] Si una cláusula BREACH: no se entrega **nada** de esa generación (fail closed), bitácora igual que ingress.
- [ ] Test: generación “python + receta” con política python-only ⇒ block, `delivered` vacío.
- [ ] Test: generación solo tutorial ⇒ delivered == texto (o sus cláusulas unidas), sin recorte silencioso.

## Tests (TDD)

```
cd backend && uv run pytest -q tests/test_sello_egreso.py --noconftest
```

## Definición de hecho

- [ ] Hold testado; cero stream especulativo
- [ ] Misma regla que ingress (no un umbral distinto “porque es salida”)
- [ ] Padre intacto
- [ ] Fila S05 → `hecho`

## Trampas

- No implementes el buffer `. ; ? \\n` del padre para “ir soltando”.
- No marques PASS interno y entregues igual.

## Prompt copiable

```
Pack Sello, ticket S05. Leé roadmap/sello/00-alcance.md.
Egreso hold en backend/sello/. Mismo decide() que S04. No perfil chat.
No toques evaluate_clause ni egress_profile del padre.
TDD tests/test_sello_egreso.py --noconftest.
Al cerrar, marcá S05 hecho en roadmap/sello/README.md.
```
