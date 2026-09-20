# Etapa 4 — ⛔ CHECKPOINT: testeo

> **Estado: HECHO** (checkpoint 2026-07-04, decisión 🟡).

> Esto NO es opcional. Es un parate deliberado para decidir si seguís derecho o corregís rumbo. Saltearlo es deployar a producción sin mirar los logs.

---

## Para qué es este checkpoint

Venís de tres etapas "de manos" (estabilizar, loguear, pulir). Antes de meterte en la parte de investigación (calibración, evidencia, benchmark) — que es lenta y donde es fácil perder semanas — parás y verificás que la **base es sólida**. Si entrás a la fase de evidencia con un sistema que crashea o loguea mal, vas a generar números basura con cara de ciencia.

---

## Checklist de salida (todo tiene que dar SÍ)

### Estabilidad
- [x] La suite de tests pasa entera, hoy, sin flaky tests. (58 tests, 2026-07-04)
- [ ] Corrí el `load_test_suite.py` y el sistema aguanta carga concurrente sin romperse.
- [x] Los flujos (chat, audit, upload, sniffer, proxy v1) andan sin crashear (cubiertos por tests de integración).
- [x] Probaste los 5 providers que el sistema declara (al menos que no crasheen al instanciarse; los de nube con key, Ollama local). — vía tests de provider wiring existentes; smoke manual de Ollama pendiente en clone fresco.

### Higiene (de Etapa 1)
- [x] Cero datos privados en repo e historial. **Confirmado, no asumido.**
- [x] `.gitignore` correcto.
- [x] README y spec dicen la verdad (tooling uv/pnpm verificado).

### Logging (de Etapa 2)
- [x] Las trazas son completas y confiables.
- [x] El export produce formato estándar.

### UX (de Etapa 3)
- [x] Se ve serio. La "screenshot money" existe y es linda.
- [x] El flujo de usuario nuevo no tiene fricciones graves.

---

## Preguntas honestas que tenés que poder responder

1. **Si un dev senior de Reddit clona el repo ahora mismo, ¿le anda al primer intento siguiendo el README?** Si la respuesta no es un sí rotundo, volvé a Etapa 1.
2. **¿Hay algo que me daría vergüenza que vean?** Código muerto, TODOs vergonzosos, comentarios en spanglish, claves de prueba hardcodeadas. Anotalo y limpialo ahora.
3. **¿El sistema hace lo que el README dice que hace?** Toda promesa del README/spec que no sea verdad es munición para que te destrocen. O lo cumplís o lo sacás del doc.

---

## Decisión del checkpoint

Al final, una de tres:
- **🟢 Verde:** todo da sí. Avanzás a Etapa 5.
- **🟡 Amarillo:** hay deuda menor pero no bloqueante. Anotala como "deuda conocida" y avanzá, pero con la lista a la vista.
- **🔴 Rojo:** hay algo que rompería un demo o un clone público. Volvés a la etapa que corresponda. **No avances en rojo.**

Escribí la decisión y la fecha acá abajo (externalizá el estado):

```
Fecha: 2026-07-04
Decisión: 🟡
Deuda conocida (si amarillo): load_test_suite.py no corrido en esta sesión (requiere backend levantado); smoke manual “clone fresco + Ollama” pendiente.
Acción (si rojo): n/a
```

---

## Prompt sugerido

```
Leé roadmap/nivel-1/etapa-4-checkpoint-testeo.md. Ayudame a ejecutar el
checkpoint: corré la suite + el load test, revisá que no haya datos privados,
y respondé con honestidad brutal las tres preguntas del doc (¿anda al primer
clone? ¿hay algo vergonzoso? ¿el README dice la verdad?). Dame un veredicto
🟢/🟡/🔴 con la lista de lo que falta para ponerlo en verde.
```
