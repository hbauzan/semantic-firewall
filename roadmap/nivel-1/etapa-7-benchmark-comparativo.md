# Etapa 7 — Benchmark comparativo

> Objetivo: correr el **mismo dataset** por al menos un baseline reconocido y poner los números lado a lado. Sin comparación, tus números no significan nada — esto es lo que faltaba en tu plan original y es lo que hace creíble el claim.

---

## Por qué esto es no-negociable

La primera pregunta de cualquier dev senior en HN o r/LocalLLaMA va a ser: **"¿comparado con qué?"** Si no tenés respuesta, el thread se muere ahí. Un número absoluto ("bloqueo el 94%") no dice nada sin un punto de referencia. Un número relativo ("bloqueo el 94% donde Llama Guard bloquea el 81% en este dataset específico") es un titular.

---

## Los baselines, por costo/valor (en tu Mac M4 16GB)

| Baseline | Qué es | Encaje en tu hardware | Por qué |
|----------|--------|------------------------|---------|
| **Llama Guard 3 1B** | Clasificador de seguridad de Meta | Liviano (~1GB), entra fácil | El más rápido de levantar; buen primer baseline |
| **Llama Guard 3 8B** | El hermano grande, más citado | Q4/Q5 quantizado (~5GB) entra; tight pero corre | El que la comunidad va a pedir sí o sí. Más credibilidad |
| **Prompt Guard (86M)** | Clasificador de jailbreak/injection de Meta | Mínimo | Ideal para tu **claim secundario** (piggybacking/injection) |

**Recomendación:** arrancá con **Llama Guard 3 1B** (encaje fácil, validás el pipeline de comparación) y **Prompt Guard** para el claim de injection. Si podés correr **Llama Guard 3 8B**, sumalo — es el que más peso le da al writeup.

> Cuidado con la RAM: 16GB unificada. **No corras tu firewall (BGE-M3) y Llama Guard 8B simultáneamente.** Hacé pasadas separadas: primero generás los veredictos del firewall sobre el dataset, los guardás, después levantás el baseline y generás los suyos. Comparás los dos archivos. Nunca los dos modelos en memoria a la vez.

---

## El framing honesto (clave)

Vos y Llama Guard **no hacen lo mismo**:
- Llama Guard **clasifica categorías de daño** (violencia, sexo, etc.). Es un clasificador entrenado.
- Vos hacés **contención geométrica de dominio**. No clasificás daño; gateás por pertenencia a un dominio.

Por eso la comparación no es "quién es mejor" en abstracto, sino **"en la tarea de allowlist-por-dominio, mi enfoque hace X, el clasificador hace Y"**. En esa tarea específica, un clasificador de daño genérico debería ser malo (no sabe qué es "tu dominio"). Ahí está tu ventaja estructural — y mostrarla honestamente es más fuerte que un "le gano en todo".

- Si **ganás** en tu tarea: titular limpio.
- Si **perdés** en alguna métrica: "enfoque distinto, ventaja arquitectónica en [auditabilidad / provider-agnosticismo / sin entrenamiento / contra modelos cerrados]". Igual tenés historia.

---

## Tareas
- [ ] Levantar Llama Guard 3 1B localmente. Correr el dataset etiquetado por él. Guardar veredictos.
- [ ] (Si entra) Idem Llama Guard 3 8B.
- [ ] Levantar Prompt Guard. Correr el subset de injection/piggybacking. Guardar veredictos.
- [ ] Tabla comparativa lado a lado: tu firewall vs. cada baseline, mismas métricas, mismo dataset.
- [ ] Análisis cualitativo: ejemplos concretos donde tu enfoque acierta y el baseline falla (y viceversa, honestamente).
- [ ] Documentar la metodología de comparación para que sea reproducible.

---

## Definición de "Etapa 7 terminada"
- [ ] Al menos un baseline corrido sobre el mismo dataset, con números lado a lado.
- [ ] Framing honesto del "no hacen lo mismo" escrito.
- [ ] Ejemplos cualitativos concretos (acierto/falla de cada uno).
- [ ] Metodología reproducible documentada.

---

## Trampas
- **No compares peras con manzanas sin avisar.** Si tu dataset favorece tu enfoque por diseño, decilo. Un crítico lo va a notar; mejor que lo digas vos.
- **No quemes la Mac.** Pasadas separadas, no modelos en paralelo.
- **No infles.** Si Llama Guard te gana en jailbreaks genéricos, está bien — vos no competís ahí, competís en allowlist de dominio. Mantené el foco en tu tarea.

---

## Presupuesto de energía
- Levantar cada baseline: 1 micro-sesión por modelo (la primera puede tener fricción de setup).
- Correr + tabular: 1-2 micro-sesiones.
- Análisis cualitativo: 1 micro-sesión.

---

## Prompts sugeridos

**Setup del baseline:**
```
Leé roadmap/nivel-1/etapa-7-benchmark-comparativo.md. Ayudame a levantar
Llama Guard 3 1B localmente en mi Mac M4 16GB y correr mi dataset etiquetado por
él, guardando los veredictos en un archivo. Recordá: pasada separada, no junto
con BGE-M3 en memoria.
```

**Tabla comparativa:**
```
Leé roadmap/nivel-1/etapa-7-benchmark-comparativo.md. Tengo los veredictos de mi
firewall y los de [baseline] sobre el mismo dataset. Generá una tabla
comparativa lado a lado con las mismas métricas, más ejemplos cualitativos
concretos donde cada uno acierta y falla. Aplicá el framing honesto de "no hacen
lo mismo": mi tarea es allowlist-por-dominio.
```
