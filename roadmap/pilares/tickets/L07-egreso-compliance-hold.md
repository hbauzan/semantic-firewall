# L07 — Egreso perfil Compliance (full hold)

> **Estado:** pendiente
> **Ola:** 3
> **Spec:** [`specs/pilar-egreso-dual-profile.md`](../specs/pilar-egreso-dual-profile.md)

## Objetivo

En perfil Compliance/CDE, **ningún token** de la generación llega al cliente hasta que la respuesta completa pasa las 4 capas del PDF (DLP rígido, anti-homoglifos, subespacios, verificación de números). Dictamen unánime o corte. Primero este perfil; el sentence buffer es L08.

## Depende de

- L04 (AND sobre oraciones de la respuesta retenida)
- L05 (embed de las oraciones; en tests se puede mockear TEI/ST)

L06 (INLP) se enchufa como capa 3 cuando exista; L07 puede shippear con seam `projection_energy` stub que falla cerrado o skip documentado si L06 sigue pendiente — no bloquees el hold.

## Desbloquea

- L08, L10, L11

## Paralelo con

- L06, L09

## Archivos a leer

- Spec egreso
- [`backend/app/api/endpoints/chat.py`](../../../backend/app/api/endpoints/chat.py) — `ui_stream_wrapper`, `stream_wrapper` (hoy reenvían el stream)
- [`backend/app/core/models.py`](../../../backend/app/core/models.py) — `ConfigState`
- [`backend/app/modules/sniffer.py`](../../../backend/app/modules/sniffer.py)

## Archivos a tocar

- `ConfigState`: `egress_profile: Literal["chat", "compliance"]` (default `compliance` hasta L08 verde, o `chat` = comportamiento actual — **documentá el default**; el PDF pide que CDE no streamee)
- `chat.py`: rama hold — absorber upstream, evaluar, emitir todo o cortar con código de perímetro
- Módulo de capas p. ej. `backend/app/modules/egress.py`
- Sniffer: no persistir secretos en claro (hash / last4)
- Tests: `backend/tests/test_egress_hold.py`
- `manifest.json` solo si cambia `state_schema`

## Fuera de alcance

- Sentence buffering (L08)
- Campañas rompepepe
- Reescribir el gate de **entrada**

## Tareas

- [ ] Buffer cerrado de la generación completa.
- [ ] Capa 1 DLP rígido: patrones de secreto de prueba (PAN con Luhn, API-key-like). BREACH si pega.
- [ ] Capa 2 normalización anti-homoglifos antes de DLP/geometría (NFKC / confusables básicos).
- [ ] Capa 3 subespacio: llamar INLP si L06 está; seam explícito.
- [ ] Capa 4 verificación determinista de números (la secuencia numérica reconstruida se testea, no solo el string crudo).
- [ ] Geometría positiva: partir la respuesta en oraciones y correr AND de L04.
- [ ] Unánime → soltar al cliente de una. Cualquier capa → no emitir payload; log de corte.
- [ ] Tests: PAN partido con newline no se entrega; respuesta on-corpus limpia sí; homoglifo que esconde dígitos dispara DLP tras normalizar.

## Tests (TDD)

Rojo: el wrapper sigue haciendo yield del upstream. Verde: con `egress_profile=compliance` el cliente no ve el PAN.

```
cd backend && uv run pytest -q tests/test_egress_hold.py
```

## Definición de hecho

- [ ] Hold cableado en `/chat` (y proxy `/v1` si comparte el wrapper; si no, documentá la deuda en el ticket cerrado)
- [ ] 4 capas invocadas; INLP opcional vía seam
- [ ] Sniffer sin secreto en claro
- [ ] Fila L07 → `hecho`

## Trampas

- Acumular para el sniffer y **igual** hacer yield al cliente es el bug actual. El hold tiene que cortar el yield.
- No loguees el PAN. last4 + hash.
- Streaming al usuario en este perfil = fallo del ticket.

## Prompt copiable

```
Usando dev-protocol, tomá roadmap/pilares/tickets/L07-egreso-compliance-hold.md.
Leé specs/pilar-egreso-dual-profile.md. Full-response hold + 4 capas. Cero tokens al cliente hasta dictamen.
No implementes sentence buffering (L08). TDD, uv run. Al cerrar, marcá L07 hecho.
```
