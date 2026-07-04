# Etapa 3 — UX y flujo de usuario

> **Estado: SIGUIENTE (en curso / pendiente).** Etapas 1–2 cerradas. Acá se retoma el trabajo de manos antes del checkpoint de la Etapa 4.

> Objetivo: embellecer y pulir el flujo. Que la herramienta se **vea** tan seria como la matemática que tiene adentro. Una herramienta de seguridad que se ve descuidada se desconfía.

---

## Por qué importa (y por qué va DESPUÉS de estabilizar)

La gente juzga credibilidad en segundos. Para un lanzamiento público, la primera captura de pantalla hace la mitad del trabajo de convencer. Pero **pulir UX sobre algo que crashea es pintar una casa que se está incendiando** — por eso va después de la Etapa 1.

Tu UX tiene un activo único: las **tres cabezas de mono** (una por filtro), los toggles ON/OFF, los `Seq` de reordenamiento, la galaxia del espacio semántico. Eso es *visualmente* contable. Sacale jugo.

---

## Tareas

### Bloque A — Coherencia visual y de marca
- [ ] Decidir la identidad: esto es el producto estrella de **Semantic Lab** (hermano de *LLM Semantic Visualizer*). Que el nombre, el logo/título y el tono sean consistentes y digan "laboratorio de seguridad semántica", no "demo de fin de semana".
- [ ] Limpiar inconsistencias de estilo en el HUD (el spec menciona extracción de estilos inline a `styles/ControlPanel.css` — verificar que esté hecho y consistente).
- [ ] Estados vacíos claros: ¿qué ve el usuario sin corpus cargado? ¿sin filtros activos? Que nunca quede una pantalla muda o confusa.

### Bloque B — Flujo del usuario nuevo
- [ ] Recorré el flujo como si fuera la primera vez: abrir → cargar PDF → activar filtros → mandar query → leer el veredicto. Anotá cada punto de fricción o confusión.
- [ ] El veredicto del firewall (PASS/BREACH con pipeline trace) tiene que ser **legible para un humano no técnico**, no solo un volcado de métricas. Que se entienda *por qué* pasó o se bloqueó.
- [ ] Tooltips: el spec menciona registro i18n de tooltips (`locales/tooltips.ts`). Verificar que cada control tenga explicación clara de qué hace y qué significa el número.

### Bloque C — La demo se cuenta sola
- [ ] Preparar un **corpus de ejemplo** y un **set de queries demo** (algunas que pasan, algunas off-topic que bloquean, una de piggybacking que bloquea) para que cualquiera que abra la herramienta vea el valor en 2 minutos. Esto reusa material que vas a necesitar igual en la Etapa 5.
- [ ] Pensar la "screenshot money": la imagen que vas a poner en el writeup. ¿Qué pantalla muestra el valor de un vistazo? Diseñá la UX para que esa pantalla exista y sea linda.

---

## Definición de "Etapa 3 terminada"
- [ ] Identidad visual coherente con Semantic Lab.
- [ ] Flujo de usuario nuevo sin fricciones ni pantallas mudas.
- [ ] El veredicto del firewall es legible para humanos.
- [ ] Existe un corpus + queries demo que cuentan la historia solos.
- [ ] Tenés clara cuál es la "screenshot money" del writeup.

---

## Trampas
- **No caigas en el pozo del pulido infinito.** El TDAH + perfeccionismo es combinación peligrosa acá. Definí "suficientemente lindo para mostrar" y parate ahí. La belleza extra es post-lanzamiento.
- **No agregues features nuevas disfrazadas de UX.** Esta etapa es pulir lo que hay, no construir. Si aparece una idea de feature, anotala en `nivel-2-futuro.md` y seguí.

---

## Presupuesto de energía
- Bloque A: 1–2 micro-sesiones.
- Bloque B: 1–2 micro-sesiones.
- Bloque C: 1 micro-sesión (parte reusa Etapa 5).

---

## Prompts sugeridos

**Auditar el flujo de usuario nuevo:**
```
Leé roadmap/nivel-1/etapa-3-ux.md, Bloque B. Arrancá la app, recorré el flujo
completo como usuario nuevo (cargar PDF, activar filtros, mandar query, leer
veredicto) y dame una lista priorizada de fricciones de UX, de la más grave a
la más cosmética. No arregles todavía — primero la lista.
```

**Hacer legible el veredicto:**
```
El veredicto del firewall hoy muestra [pegar ejemplo]. Quiero que un humano no
técnico entienda por qué pasó o se bloqueó, sin perder las métricas duras para
el que las quiera. Proponeme un rediseño del mensaje de veredicto y aplicalo en
ChatInterface.tsx.
```
