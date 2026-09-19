# L08 — Egreso perfil Chat (sentence buffering)

> **Ticket histórico (hecho, pack cerrado).** No lo tomes. No corras el prompt copiable. Código en `main`: PRs #4–#15.

> **Estado:** hecho
> **Ola:** 3
> **Spec:** [`specs/pilar-egreso-dual-profile.md`](../specs/pilar-egreso-dual-profile.md) § perfil Chat.

## Objetivo

Con `egress_profile=chat`, acumular tokens hasta delimitador de oración (`. ; ? \n`), evaluar la cláusula (TEI + política ya existente: AND L04, capas que apliquen), y o bien soltar una ráfaga o cortar el SSE. El perfil `compliance` de L07 sigue siendo hold completo.

## Depende de

- L07 (hold estable; Chat es el segundo perfil, no un atajo)

## Desbloquea

- L12 (campaña de fragmentación contra el acumulador)

## Paralelo con

Nada. No empieces L08 si L07 no está `hecho`.

## Archivos a leer

- Spec egreso
- `chat.py` post-L07
- [`backend/app/core/firewall.py`](../../../../backend/app/core/firewall.py) `segment()` — el acumulador de **salida** es otro objeto; no reuses ciegamente el splitter de prompts si no respeta `. ; ? \n` del PDF

## Archivos a tocar

- Acumulador p. ej. `backend/app/modules/sentence_buffer.py`
- Rama `egress_profile=chat` en `chat.py`
- Tests: `backend/tests/test_sentence_buffer.py`

## Fuera de alcance

- Cambiar las 4 capas de compliance
- Relajar hold en perfil CDE
- Campañas

## Tareas

- [x] Parser: delimitadores `. ; ? \n`. Oración congelada → eval async.
- [x] PASS → flush al cliente. BREACH → abort SSE, tirar buffer, código de corte, log.
- [x] Texto sin delimitador final: al `done` del upstream, evaluar el resto como cláusula (no fugar el tail sin gate).
- [x] Tests unitarios del acumulador (sin LLM): “hola. mundo” → dos evals; BREACH en la segunda no emite la segunda; PAN cortado por `\n` — **documentá** que este perfil puede emitir la primera mitad (es el motivo de L07). No “arregles” eso acá mezclando hold.
- [x] Test de integración del wrapper con upstream mockeado (lista de deltas).

## Tests (TDD)

```
cd backend && uv run pytest -q tests/test_sentence_buffer.py
```

## Definición de hecho

- [x] Perfil chat ≠ perfil compliance
- [x] Tail de stream también se evalúa
- [x] L07 no regresiona
- [x] Fila L08 → `hecho`

Cerrado 2026-09-18. Acumulador `SentenceBuffer` (`. ; ? \\n`), no el splitter de ingress. Tail al `done`. Chat puede emitir la primera mitad de un PAN partido por newline — L07 hold no se mezcló. AND en chat se salta si no hay pack (HUD); DLP/números/INLP sí corren. `firewall.py` intacto.

## Trampas

- Emitir tokens “para que se sienta streaming” antes del delimitador viola el spec.
- No uses el LLM real en el unit test.

## Prompt copiable (NO EJECUTAR)

> Pack cerrado. Este bloque es registro. No lo copies a un agente.


```
Usando dev-protocol, tomá roadmap/pilares/tickets/L08-egreso-chat-sentence-buffer.md.
Leé specs/pilar-egreso-dual-profile.md. Sentence buffering solo si egress_profile=chat.
No toques el hold de compliance. TDD, uv run. Al cerrar, marcá L08 hecho.
```
