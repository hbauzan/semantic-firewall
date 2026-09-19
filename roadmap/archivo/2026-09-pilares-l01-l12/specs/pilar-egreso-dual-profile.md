# Egreso — dual-profile (Chat vs Compliance)

> **Snapshot histórico del pack L01–L12 (cerrado 2026-09-18/19).** La verdad es el código en `main`. Estas specs describen el destino del pack; varias líneas “código hoy” quedaron viejas a propósito. No reimplementar.

> Fuente: PDF, Documento 4 / Parte 2.2.
> Tickets: [L07](../tickets/L07-egreso-compliance-hold.md), [L08](../tickets/L08-egreso-chat-sentence-buffer.md).
> Código hoy: [`backend/app/api/endpoints/chat.py`](../../../../backend/app/api/endpoints/chat.py) — `ui_stream_wrapper` / `stream_wrapper` acumulan tokens **para el sniffer** y los reenvían al cliente sin evaluar. No hay corte de egreso.

---

## El dilema

- UX: el usuario espera SSE inmediato (&lt; 1 s percibido).
- Seguridad: evaluar al final (5–15 s) llega tarde; soltar tokens sin control deja fugar secretos antes del corte.

---

## Perfil 1 — Interactivo / Chat (L08)

Speculative sentence buffering:

```
tokens LLM --> acumulador RAM
                 |
         delimitador (. ; ? \n)
                 |
         oración congelada (~15–40 tokens)
                 |
         inferencia async TEI
            /          \
         PASS           BREACH
     ráfaga al cliente  corte SSE + log
```

1. Nada se emite hasta oración completa.
2. Parser liviano de fin de cláusula.
3. Embed + política (AND multi-grano / INLP según lo ya promovido a este path).
4. PASS → ráfaga. BREACH → abortar conexión, descartar buffer, código de corte perimetral.

Target: asistencia, chat de manual. Política de corte: oración.

---

## Perfil 2 — Compliance / CDE / PCI-DSS (L07)

Sentence buffering **no alcanza** para secretos estructurados: un PAN de 16 dígitos partido por un salto de línea entrega la primera mitad antes de que la segunda dispare el detector.

Mecanismo: **retención completa**. El stream del LLM se absorbe en un buffer cerrado de backend. Se audita en paralelo por las 4 capas; se libera al usuario **solo** con dictamen unánime.

Las 4 capas del PDF:

1. DLP rígido
2. Normalización anti-homoglifos
3. Subespacios ortogonales (Pilar 1 / L06)
4. Verificación determinista de números

Target: CDE, datos de tarjetahabiente, secretos industriales. Streaming al usuario en este perfil es un bug.

**Orden de implementación:** L07 (hold) primero; L08 (buffer por oración) después.

---

## Configuración

Un flag de perfil de egreso (nombre a elegir en config: p. ej. `egress_profile: chat | compliance`). Default de desarrollo puede ser `compliance` hasta que L08 esté verde: más auditable, menos teatro de tokens.

El sniffer no debe persistir secretos en claro cuando el perfil es compliance (last4 / hash). L07 lo incluye porque el PDF pide evidencia de corte perimetral sin convertir el log en incidente.
