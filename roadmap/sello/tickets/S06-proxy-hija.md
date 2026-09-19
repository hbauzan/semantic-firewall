# S06 — Proxy hija OpenAI-compatible

> **Estado:** pendiente
> **Ola:** 4
> **Spec:** [`../00-alcance.md`](../00-alcance.md)

## Objetivo

Un HTTP **aparte** del FastAPI padre: `POST /v1/chat/completions` (y si hace falta un `/chat` mínimo) que corre S04 en ingress, llama un LLM libre atrás, y suelta solo lo que S05 hold aprueba. El modelo no es el juez.

## Depende de

- S04, S05

## Desbloquea

Nada en este pack. Cierra la herramienta hija usable contra Ollama u otro OpenAI-compatible.

## Paralelo con

Nada.

## Archivos a leer

- [`../00-alcance.md`](../00-alcance.md) — superficie hija
- Proxy padre (`POST /v1/chat/completions`) **como referencia de shape**, no para editarlo
- Seam de provider del padre: Sello tiene el suyo (URL + modelo por env)

## Archivos a tocar

- `backend/sello/proxy.py` (o `backend/sello/http/`) — proceso o router **no** montado en `evaluate_clause`
- Entrypoint: `uv run python -m sello.proxy` (puerto propio, default distinto del padre)
- Tests: `backend/tests/test_sello_proxy.py` — LLM **mock** (httpx/ASGI)

## Fuera de alcance

- Editar `backend/app/core/firewall.py`, rutas `/chat` / `/v1` del padre
- TEI, segundo BGE, campañas rompepepe
- Auth de producto, HUD, n8n
- Streaming SSE de tokens (hold primero; si hay stream, es después del hold o no hay)

## Tareas

- [ ] App ASGI mínima: healthz + `/v1/chat/completions`.
- [ ] Ingress S04 sobre `messages[-1]`. BREACH ⇒ 403 o cuerpo de corte **sin** eco del prompt.
- [ ] Upstream por env (`SELLO_UPSTREAM_URL`, `SELLO_UPSTREAM_MODEL`). Timeout explícito.
- [ ] Hold S05 sobre la respuesta. BREACH ⇒ no se entrega la generación.
- [ ] Tests: mock upstream; piggy de tres cláusulas con política python-only ⇒ no llama al LLM o no entrega receta.
- [ ] Documentar en `backend/sello/README.md` cómo levantar hija + Ollama.

## Tests (TDD)

```
cd backend && uv run pytest -q tests/test_sello_proxy.py --noconftest
```

## Definición de hecho

- [ ] Proxy testeado con LLM mock
- [ ] Puerto / módulo distintos del padre
- [ ] Padre intacto
- [ ] Fila S06 → `hecho`

## Trampas

- No montes Sello como middleware de `evaluate_clause`.
- No streamees y “audites después”.
- No cargues BGE-M3 en el test del proxy.

## Prompt copiable

```
Pack Sello, ticket S06. Leé roadmap/sello/00-alcance.md.
Proxy hija OpenAI-compatible en backend/sello/. Usa S04+S05. LLM mock en tests.
No edites el FastAPI padre ni evaluate_clause.
TDD tests/test_sello_proxy.py --noconftest.
Al cerrar, marcá S06 hecho en roadmap/sello/README.md.
```
