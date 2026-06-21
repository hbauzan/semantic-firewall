# Nivel 2 — Bidireccional (futuro plausible)

> Solo ideas. No trabajar en esto hasta cerrar el Nivel 1 y que tenga algo de tracción. Esto es "hacia dónde puede ir", no "lo próximo que hago".

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

## Preguntas abiertas para cuando llegue el momento
- ¿Buffer completo vs. filtrado incremental en el stream?
- ¿Qué se le muestra al usuario cuando la salida se bloquea a mitad de stream?
- ¿La región de salida prohibida es la misma que la de entrada, o se configuran por separado?
- ¿Cómo se audita una respuesta bloqueada sin loguear el contenido sensible que se bloqueó?

---

## Cuándo abrir este archivo de nuevo
Cuando el Nivel 1 esté publicado, tenga tracción, y sientas que el siguiente paso natural es la simetría entrada/salida. Ni antes.
