# Etapa 8 — ⛔ CHECKPOINT: ¿los números cuentan una historia honesta?

> **Estado: pendiente** (después de etapas 5–7).

> Segundo parate obligatorio. Antes de gastar energía en redactar y publicar, verificás que tenés algo que valga la pena publicar.

---

## Para qué es este checkpoint

Acabás de generar evidencia (Etapa 6) y comparación (Etapa 7). Antes de meterte en la redacción del writeup y el lanzamiento — que es donde exponés tu nombre — parás y mirás los números con frialdad. La pregunta no es "¿gané?". Es **"¿tengo una historia honesta y defendible?"**.

Una historia honesta donde perdés en algo pero ganás en tu nicho **es publicable y respetable**. Una historia inflada donde "gano en todo" es un suicidio reputacional en cuanto alguien reproduce y no le da.

---

## Checklist de salida

- [ ] Tenés un **número primario** (allowlist) reproducible, con baseline.
- [ ] Tenés el **número del claim secundario** (piggybacking) con o sin segmentación.
- [ ] Tenés el **número diferenciador** (aporte de excitación sobre coseno).
- [ ] Probaste determinismo y documentaste sus límites.
- [ ] Tenés ejemplos cualitativos concretos (no solo tablas).
- [ ] Sabés **dónde tu herramienta falla** y lo podés decir con tranquilidad.

---

## Las preguntas frías

1. **¿Cuál es el titular de una sola línea?** Si no lo podés decir en una frase, todavía no tenés la historia. Ejemplo: *"Un firewall geométrico local bloquea el N% de queries fuera-de-dominio donde un clasificador de daño genérico bloquea el M%, sin tocar el modelo y con traza auditable de cada decisión."*

2. **¿Qué va a decir el comentario más hostil de HN, y tengo respuesta?** Anticipá los tres ataques más probables:
   - "Esto es solo un threshold de similitud coseno con pasos extra." → Respuesta: el experimento de excitación-sobre-coseno (Etapa 5).
   - "BGE-M3 no es determinista cross-hardware, tu 'firma' no sirve." → Respuesta: el determinismo está acotado al deployment, lo decís explícito, y es suficiente para el caso de uso.
   - "Esto no escala / el corpus poisoning lo rompe." → Respuesta: corpus es trusted por diseño (lo carga un admin autenticado); está fuera del threat model declarado.

3. **¿Estoy listo para que reproduzcan y no me dé igual?** Si la respuesta es "ojalá nadie reproduzca", no estás listo. La evidencia tiene que aguantar reproducción.

---

## Decisión del checkpoint

```
Fecha: ____________
Titular de una línea: 
Decisión: 🟢 publicar / 🟡 ajustar evidencia / 🔴 falta historia
Los 3 ataques anticipados y mis respuestas:
  1.
  2.
  3.
```

- **🟢:** Avanzás a Etapa 9 (lanzamiento).
- **🟡:** La historia está pero algún número es débil o falta una limitación documentada. Volvé puntualmente a Etapa 6/7.
- **🔴:** No tenés historia todavía. Mejor saberlo ahora que después del post. Volvé a Etapa 5 a buscar el ángulo real.

---

## Prompt sugerido

```
Leé roadmap/nivel-1/etapa-8-checkpoint.md. Con todos los resultados de las
Etapas 6 y 7 a la vista, ayudame a contestar las preguntas frías: ¿cuál es el
titular de una línea? ¿cuáles son los 3 ataques más probables de HN y mi mejor
respuesta a cada uno? Dame un veredicto honesto 🟢/🟡/🔴 sobre si tengo una
historia publicable.
```
