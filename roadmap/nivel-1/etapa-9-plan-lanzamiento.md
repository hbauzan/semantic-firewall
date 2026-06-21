# Etapa 9 — Plan de lanzamiento

> Objetivo: convertir la evidencia en un **artefacto público que trabaja solo** y publicarlo en una secuencia adaptada a tu realidad (solo, sin red de contactos, energía intermitente). El artefacto hace el trabajo; vos no tenés que hacer networking.

---

## El principio que rige todo el lanzamiento

> **El objetivo no es engagement. Es producir un artefacto al que después puedas linkear** en un CV, un mensaje a un recruiter, una conversación. Los posts son tráfico temporal; el writeup + el repo son el activo permanente.

La gente seria que te quiera contratar **no comenta en el thread, te escribe por DM**. Diseñá para eso: que el material se defienda solo mientras dormís.

---

## Parte 1 — El writeup (el activo permanente)

Un artículo en inglés (tu audiencia es global: HN, r/LocalLLaMA). En tu propio blog o Medium/Substack — algo que controlás y que sobrevive a los posts.

**Estructura recomendada:**

1. **El gancho (1 párrafo).** El problema real, desde tu lugar: "20 años de PCI/DSS me enseñaron que no podés confiar en que un sistema 'se porte bien' — tenés que cercar lo que puede hacer. Apliqué esa intuición a los LLMs."

2. **La idea, con la metáfora de la galaxia.** Espacio del embedder = universo; corpus = galaxia; firewall = frontera. Positivo/negativo. La "lobotomía virtual" (cirujano con chaperón). Acá podés usar una imagen del *LLM Semantic Visualizer* — visual vale 100x una tabla.

3. **Por qué geometría y no clasificación.** El argumento coseno-es-un-promedio → la excitación cierra la compensación. Tu diferenciador, explicado para devs.

4. **El método.** Cómo medís. Dataset, calibración Youden, determinismo. Honestidad metodológica.

5. **Resultados.** Tus números + el baseline lado a lado. Incluí **dónde falla**. La screenshot money.

6. **Limitaciones (sección explícita, NO la escondas).** Determinismo acotado al deployment. Corpus trusted (fuera de scope el poisoning). Top-1 vector para la decisión. Decilas vos antes que te las digan.

7. **Implicaciones / hacia dónde va (Nivel 2 y 3, como visión).** Bidireccional. Firmas certificables. Acá soltás la visión grande — pero recién al final, después de haber demostrado que el Nivel 1 anda.

8. **Repo + cómo reproducir.** Link, comando exacto, dataset. Invitá a reproducir.

**Reglas del writeup:**
- Lidera con Nivel 1, cierra con visión. Nunca al revés.
- Toda afirmación, respaldada o etiquetada como especulación.
- Tu background PCI/DSS al frente — es tu credibilidad, no tu vergüenza.

---

## Parte 2 — El repo público

- README en inglés, limpio, con la "screenshot money" arriba de todo.
- Instrucciones de instalación que **funcionen al primer intento** (lo verificaste en Etapa 4).
- Sección de reproducción de resultados.
- **Licencia: AGPL-3.0** (decidido). Es copyleft fuerte y, a diferencia de GPL, **cierra el agujero SaaS**: como tu firewall se sirve como API por red, AGPL obliga a publicar el código fuente también a quien lo corra **como servicio** (no solo a quien redistribuya el binario). Es exactamente "quien la use, publica su código". Agregá el archivo `LICENSE` con el texto AGPL-3.0 y el header SPDX (`SPDX-License-Identifier: AGPL-3.0-or-later`) en los fuentes principales.
- **Cero datos privados** (verificado en Etapa 1, re-verificá acá).

---

## Parte 3 — Secuencia de publicación (adaptada a vos)

En este orden, **con días/semanas de diferencia**, no todo junto (te quema y no podés atender la reacción):

1. **Hacker News (Show HN).** Primero. Audiencia técnica, lectura justa pero exigente. Si pasa HN, pasa cualquier cosa. Título sobrio y descriptivo, sin hype. Posteá un día de semana a la mañana (hora US). **Quedate disponible las primeras 2-3 horas para responder comentarios** — es lo único que requiere tu presencia activa, y vale la pena.

2. **r/LocalLLaMA.** Tu comunidad natural: reciben muy bien herramientas locales con matemática interesante. Menos hostil que r/MachineLearning. Acá tu encaje es perfecto (local, auditable, sin nube obligatoria).

3. **LinkedIn.** Después, cuando ya tenés validación técnica que mostrar. Acá el framing es profesional: "construí X, esto es lo que aprendí sobre seguridad de IA". Es donde los recruiters miran. Linkeá al writeup, no repitas el contenido.

4. **(Opcional, con cuidado) r/MachineLearning.** Solo si el writeup está MUY pulido. Es hostil con no-académicos y exigente con el rigor formal. Alto riesgo, alta recompensa. Podés saltearlo sin perder nada.

**Lo que NO tenés que hacer:** no necesitás Twitter/X diario, ni newsletter, ni "construir audiencia". Eso es trabajo de creador de contenido, no tu objetivo. Un buen artefacto + tres posts bien puestos alcanza.

---

## Parte 4 — Material de apoyo (preparar ANTES de postear)
- [ ] La "screenshot money" (de Etapa 3).
- [ ] Un GIF o video corto (30-60s) del firewall bloqueando un piggybacking en vivo. Mucho más convincente que texto.
- [ ] Las respuestas a los 3 ataques anticipados (de Etapa 8), listas para pegar en comentarios.
- [ ] Un párrafo de "quién soy" reusable para el DM que te van a mandar.

---

## Definición de "Etapa 9 terminada" (= Nivel 1 terminado)
- [ ] Writeup publicado, con la estructura de arriba.
- [ ] Repo público limpio, reproducible, sin datos privados.
- [ ] Material de apoyo listo (screenshot, GIF, respuestas).
- [ ] Posteado en HN y r/LocalLLaMA, con LinkedIn en cola.

---

## Trampas
- **No publiques todo el mismo día.** Te quema y no podés atender la reacción. Espaciá.
- **No respondas a la hostilidad con hostilidad.** Si alguien te ataca, respondé con datos o agradecé el punto. La compostura pública es parte del artefacto.
- **No esperes a que esté "perfecto".** Perfecto no existe y el TDAH + perfeccionismo te puede dejar acá para siempre. "Honesto, reproducible y bien explicado" es el listón, no "perfecto".
- **No prometas el Nivel 2/3 con fechas.** Es visión, no compromiso. "Hacia dónde va", nunca "lo próximo que sale".

---

## Presupuesto de energía
- Writeup: en pedazos, sección por sección. La parte más larga. No la hagas de una.
- Repo cleanup: 1-2 micro-sesiones.
- Material de apoyo: 1-2 micro-sesiones.
- Posteo: el día de cada post + ventana de respuesta. Elegí días donde tengas energía y tiempo.

---

## Prompts sugeridos

**Esqueleto del writeup:**
```
Leé roadmap/nivel-1/etapa-9-plan-lanzamiento.md, Parte 1. Con todos mis
resultados de las Etapas 6 y 7, ayudame a escribir el writeup en inglés siguiendo
la estructura de 8 secciones. Empecemos por el gancho y la sección de método.
Lidera con el Nivel 1, dejá la visión para el final. Mi background es PCI/DSS,
ponelo al frente.
```

**Preparar el repo público:**
```
Leé roadmap/nivel-1/etapa-9-plan-lanzamiento.md, Parte 2. Ayudame a dejar el
repo listo para público: README en inglés con la screenshot arriba, instrucciones
que anden al primer clone, sección de reproducción de resultados, y una
re-verificación final de que no quedó ningún dato privado en el repo ni en el
historial.
```

**Redactar el Show HN:**
```
Leé roadmap/nivel-1/etapa-9-plan-lanzamiento.md, Parte 3. Ayudame a redactar el
título y el texto de un "Show HN" sobrio y sin hype para mi firewall geométrico,
y preparemos las respuestas a los 3 ataques más probables de la Etapa 8 para
tenerlas listas en comentarios.
```
