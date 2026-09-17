# Nivel 2 — Bidireccional

> Visión. El trabajo cortado en tickets está en [`../pilares/`](../pilares/README.md) (PDF de 4 pilares, L01–L12). Este archivo no se ejecuta.

---

## La idea en una línea

Hoy filtrás la **entrada** al LLM. El Nivel 2 filtra también la **salida**: vectorizás la respuesta del modelo y la comparás contra la región prohibida (o exigís que caiga dentro de la permitida) **antes de mostrarla al usuario**.

---

## Por qué tiene demanda real

- **Soberanía de datos / cumplimiento regional.** Tu ejemplo de China: una versión que no deja que el LLM emita respuestas dentro de cierta región semántica. Misma matemática, otra dirección del flujo.
- **Prevención de fuga en la salida.** Aunque el prompt pase, el LLM podría generar algo que toca datos sensibles (un PAN, un secreto). Filtrar la salida es la otra mitad de un DLP semántico.
- **Defensa contra ataques que se manifiestan en la respuesta**, no en el prompt.

---

## Lo que cambia respecto al Nivel 1

| Nivel 1 (entrada) | Nivel 2 (salida) |
|-------------------|------------------|
| Filtrás antes de generar | Filtrás después de generar (ya gastaste el cómputo) |
| Latencia baja, bloqueo limpio | Tenés que decidir: ¿buffer toda la respuesta antes de mostrar? ¿filtrar por chunks en el stream? |
| Una pasada por embedder | Pasada de generación + pasada de embedding de la salida |

**El problema duro nuevo:** el streaming. Si filtrás la salida, o bufferizás todo (matás el efecto "streaming" y subís latencia percibida) o filtrás chunk a chunk (y tenés que decidir qué hacer cuando ya emitiste parte de una respuesta que después resulta prohibida). Decisión de diseño no trivial.

---

## Preguntas que el pack de pilares ya cortó

| Pregunta | Dónde se responde |
| :--- | :--- |
| ¿Buffer completo vs. incremental? | Dual-profile: Compliance = hold (L07); Chat = oración (L08) |
| ¿Qué ve el usuario en un corte a mitad? | L08: abort SSE + código de perímetro; L07: nada hasta dictamen |
| ¿Región de salida vs entrada? | AND multi-grano (L04) + INLP (L06) sobre la generación |
| ¿Auditar sin loguear el secreto? | L07: sniffer hash/last4 |

Análisis previo (no ejecutar): [`../archivo/README.md`](../archivo/README.md).

---

## Cuándo abrir este archivo de nuevo

Para **implementar**, no: tomá un ticket en [`../pilares/`](../pilares/README.md). Volvé acá solo si cambia la visión de Nivel 2 (no el detalle de L0x).
