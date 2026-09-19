# Pilar 1 — Blanqueamiento e INLP

> **Snapshot histórico del pack L01–L12 (cerrado 2026-09-18/19).** La verdad es el código en `main`. Estas specs describen el destino del pack; varias líneas “código hoy” quedaron viejas a propósito. No reimplementar.

> Fuente: PDF, Pilar 1 y Parte 2.1.
> Tickets: [L02](../tickets/L02-blanqueamiento-offline.md), [L06](../tickets/L06-inlp-y-tau.md).
> Código hoy: [`backend/app/core/firewall.py`](../../../../backend/app/core/firewall.py) (`run_excitation_filter`: conteo \(|Q_i-C_i|\le\varepsilon\) en la base canónica de BGE-M3).

---

## Por qué comparar coordenadas crudas falla

En un espacio de embedding (BGE-M3, 1024D) los ejes no son comparables:

- Un eje de estilo/sintaxis puede variar en un rango ancho (p. ej. 10–100). Una diferencia de 8 es prosa normal (formal vs coloquial) y un umbral fijo ciego la marca como incumplimiento → falso positivo.
- Un eje de núcleo técnico puede vivir apretado (p. ej. 1.0–2.0). Un salto de 0.8 es un desvío conceptual grande, pero si el umbral ciego es 3, pasa → falso negativo / fuga.

La excitación actual trata todos los ejes igual. Eso es el bug.

---

## Blanqueamiento

$$
Q' = (Q - \mu)\,\Sigma^{-1/2}
$$

1. **Centrar.** \(Q - \mu\) mueve el centro de masa del corpus a origen.
2. **Blanquear.** \(\Sigma^{-1/2}\) (raíz inversa de la covarianza del corpus) estira/comprime cada eje por su dispersión real y deshace correlaciones.
3. **Resultado.** En \(Q'\) cada eje tiene varianza 1. Una diferencia de \(1.0\) es un desvío de 1 desviación estándar (z-score). Recién ahí una comparación dimensión a dimensión es coherente.

\(\mu\) y \(\Sigma\) se estiman **sobre los vectores del corpus versionado**, no sobre queries sueltas.

Este pack no pide “otro \(\varepsilon\) sobre BGE-M3 crudo”. Pide cambiar de base.

---

## Subespacio ortogonal (INLP) y umbral \(\tau\)

Un concepto prohibido no es un punto con una esfera alrededor. El atacante empuja el vector con contexto inocuo (“obra de teatro histórica…”) y sale de la burbuja.

1. **Subespacio \(P\).** Se aíslan las direcciones que definen el tema prohibido, independiente del tono.
2. **Proyección \(\Pi_P(Y)\).** Sombra del vector de texto sobre ese eje. El relleno contextual proyecta en otras direcciones.
3. **Energía \(\|\Pi_P(Y)\|^2\).** Cuánta masa apunta a lo prohibido.
4. **Umbral \(\tau\).** Si la sombra supera \(\tau\), corte. No importa el disfraz.

### Calibración empírica (rompepepe)

\(\tau\) no se inventa:

- 100 prompts benignos complejos + 100 ataques de evasión.
- Graficar \(\|\Pi_P\|^2\) en los 200.
- Esperable: benignos en sombras chicas; evasiones disfrazadas en sombras notables.
- Fijar \(\tau\) en el punto que da 0 bloqueos legítimos y máxima intercepción adversarial.

Hasta que exista el Oracle ([L09](../tickets/L09-oraculo-y-metricas.md)), L06 puede usar un golden set estático etiquetado del mismo tamaño; L09 sustituye el set estático cuando esté listo.

---

## Relación con el filtro actual

| Pieza | Hoy | Este pilar |
| :--- | :--- | :--- |
| Excitación | Hamming L∞ en ejes crudos, \(\varepsilon\) fijo | Solo después de blanquear, si se reusa un conteo por eje |
| Coseno | Sigue existiendo como filtro de entrada Nivel 1 | No se borra en este spec; el lab mide el espacio blanqueado aparte |
| INLP | No existe | Capa de tema prohibido + \(\tau\) |

No reescribir `evaluate_clause()` en L02. Laboratorio primero.
