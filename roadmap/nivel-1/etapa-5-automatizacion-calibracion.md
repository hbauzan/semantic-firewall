# Etapa 5 — Automatización de calibración

> Objetivo: un harness que, dado un corpus, **encuentre la mejor calibración de thresholds** y mida cómo se comporta el firewall. Acá empieza la parte de investigación — el corazón del valor.

---

## La pregunta de fondo que esta etapa responde

Hoy los thresholds (cosine 0.5315, excitation 150, noise 4.5) vienen de una calibración Youden previa. Pero:
- ¿Esos números son óptimos para **cualquier** corpus, o solo para el que se calibró?
- ¿La **excitación dimensional** realmente agrega señal sobre el coseno, o es redundante? (esto es tu claim diferenciador — hay que **medirlo**, no afirmarlo)
- ¿Cuánto cambia la frontera óptima entre un corpus médico y uno financiero?

Sin esta etapa, tu afirmación "la excitación cierra la compensación del coseno" es teórica. Con esta etapa, es **medida**.

---

## Lo que necesitás construir

### Pieza 1 — Dataset etiquetado (lo más importante)
Un conjunto de queries con etiqueta de verdad:
- **DEBE PASAR**: queries legítimas, on-corpus (preguntas reales sobre el dominio del PDF).
- **DEBE BLOQUEAR (off-topic)**: queries de otros dominios (la galaxia equivocada).
- **DEBE BLOQUEAR (adversarial)**: jailbreaks y, sobre todo, **piggybacking** (cláusula benigna + cláusula maliciosa concatenadas) — tu claim secundario.

Fuentes: AdvBench y HarmBench para adversarial (subsets, no todo). Las on-corpus las generás vos del dominio del PDF (incluso con ayuda de un LLM: "generá 50 preguntas legítimas sobre este documento"). Las off-topic, de cualquier corpus de otro dominio.

> **Empezá CHICO y A MANO.** 20-30 queries etiquetadas a mano, corridas manualmente, ANTES de automatizar nada. Si tu harness automatizado tiene un bug y nunca mediste a mano primero, tus 10.000 corridas dan números basura con cara de ciencia. Esto es R&D 101.

### Pieza 2 — Barredor de thresholds (threshold sweep)
- Para un corpus dado, barré rangos de `cosine_threshold`, `excitation_threshold`, `noise_limit`.
- Para cada combinación, corré el dataset etiquetado y registrá verdaderos/falsos positivos/negativos.
- Calculá la curva ROC y el punto Youden-óptimo por filtro.
- Esto extiende lo que ya tenés (`db_stress_suite.py`, la calibración Youden mencionada en spec §11.11).

### Pieza 3 — El experimento clave: ¿excitación aporta sobre coseno?
- Corré el dataset con **solo coseno** activo → registrá qué adversariales pasan.
- Corré con **coseno + excitación** → registrá cuántos de esos que pasaban ahora bloquean.
- **Ese número — "adversariales que el coseno deja pasar pero la excitación bloquea" — es la evidencia central de tu claim diferenciador.** Si es alto, tenés titular. Si es ~0, tu tercera cabeza es redundante y necesitás saberlo (mejor vos que un comentarista de HN).

---

## Tareas
- [ ] Armar el dataset etiquetado chico (20-30) a mano. Correrlo manualmente. Validar que los resultados tienen sentido.
- [ ] Expandir el dataset (cientos de queries) usando las fuentes de arriba.
- [ ] Construir el threshold sweep automatizado sobre dataset isolado (sin tocar el corpus de producción — reusar el patrón de DB temporal de `db_stress_suite.py`).
- [ ] Generar curvas ROC y punto Youden-óptimo por corpus.
- [ ] Correr el experimento coseno-solo vs. coseno+excitación. Registrar el número clave.
- [ ] Probar con **al menos 2 corpus de dominios distintos** para ver cuánto se mueve la frontera óptima.

---

## Definición de "Etapa 5 terminada"
- [ ] Dataset etiquetado, versionado, con su metodología documentada.
- [ ] Harness de calibración que dado un corpus produce thresholds óptimos + ROC.
- [ ] Tenés el número de "aporte de la excitación sobre el coseno", medido en ≥2 corpus.
- [ ] Sabés cuánto cambia la calibración entre dominios (justifica el "recalibrá al cambiar de corpus").

---

## Trampas
- **A mano primero, siempre.** Ya lo dije dos veces. Es la trampa más cara del proyecto.
- **No te enamores de un solo corpus.** Si calibrás y medís contra un único PDF, no sabés si generaliza. Mínimo dos dominios.
- **Cuidado con el data leakage:** las queries on-corpus no pueden ser citas textuales del PDF (eso infla la métrica). Tienen que ser preguntas *sobre* el contenido, no copias de él.
- **Determinismo primero.** Antes de barrer thresholds, confirmá que el mismo prompt da el mismo vector en N corridas (ver Etapa 6, Bloque determinismo). Si el embedder no es determinista en tu máquina, toda la calibración es ruido.

---

## Presupuesto de energía
Esta es la etapa más lenta y más valiosa. No la apures.
- Dataset a mano: 1-2 micro-sesiones.
- Dataset expandido: 1-2 micro-sesiones.
- Harness de sweep: varias micro-sesiones (es lo más técnico).
- Experimentos: 1-2 micro-sesiones de correr + leer.

---

## Prompts sugeridos

**Arrancar a mano (no automatizar todavía):**
```
Leé roadmap/nivel-1/etapa-5-automatizacion-calibracion.md. Antes de automatizar
nada, ayudame a armar un dataset etiquetado CHICO (unas 25 queries: on-corpus
que deben pasar, off-topic que deben bloquear, y piggybacking que debe bloquear)
para el corpus [X]. Corramos esas queries a mano contra el firewall y validemos
que los veredictos tienen sentido. Sin automatización todavía.
```

**El experimento clave:**
```
Leé roadmap/nivel-1/etapa-5-automatizacion-calibracion.md, Pieza 3. Quiero medir
si la excitación dimensional aporta sobre el coseno. Corré el dataset etiquetado
dos veces: (1) solo filtro coseno activo, (2) coseno + excitación. Reportame
cuántos adversariales pasan el coseno pero los bloquea la excitación. Ese es el
número que más me importa.
```

**Construir el threshold sweep:**
```
Leé roadmap/nivel-1/etapa-5-automatizacion-calibracion.md, Pieza 2. Construí un
harness que, sobre una DB temporal aislada (como db_stress_suite.py), barra
rangos de cosine/excitation/noise thresholds contra el dataset etiquetado,
calcule la curva ROC y el punto Youden-óptimo por filtro. Que NO toque el corpus
de producción. Mostrame el diseño antes de implementar.
```
