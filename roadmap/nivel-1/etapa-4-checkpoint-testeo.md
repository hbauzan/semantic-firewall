# Etapa 4 — ⛔ CHECKPOINT: testeo

> **Estado: pendiente.** Se ejecuta **después** de cerrar la Etapa 3. Los ítems de higiene/logging de abajo ya se cumplieron en etapas 1–2, pero en este checkpoint hay que **reconfirmarlos hoy**, no asumirlos.

> Esto NO es opcional. Es un parate deliberado para decidir si seguís derecho o corregís rumbo. Saltearlo es deployar a producción sin mirar los logs.

---

## Para qué es este checkpoint

Venís de tres etapas "de manos" (estabilizar, loguear, pulir). Antes de meterte en la parte de investigación (calibración, evidencia, benchmark) — que es lenta y donde es fácil perder semanas — parás y verificás que la **base es sólida**. Si entrás a la fase de evidencia con un sistema que crashea o loguea mal, vas a generar números basura con cara de ciencia.

---

## Checklist de salida (todo tiene que dar SÍ)

### Estabilidad
- [ ] La suite de tests pasa entera, hoy, sin flaky tests.
- [ ] Corrí el `load_test_suite.py` y el sistema aguanta carga concurrente sin romperse.
- [ ] Los flujos (chat, audit, upload, sniffer, proxy v1) andan sin crashear.
- [ ] Probaste los 5 providers que el sistema declara (al menos que no crasheen al instanciarse; los de nube con key, Ollama local).

### Higiene (de Etapa 1)
- [ ] Cero datos privados en repo e historial. **Confirmado, no asumido.**
- [ ] `.gitignore` correcto.
- [ ] README y spec dicen la verdad.

### Logging (de Etapa 2)
- [ ] Las trazas son completas y confiables.
- [ ] El export produce formato estándar.

### UX (de Etapa 3)
- [ ] Se ve serio. La "screenshot money" existe y es linda.
- [ ] El flujo de usuario nuevo no tiene fricciones graves.

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
Fecha: ____________
Decisión: 🟢 / 🟡 / 🔴
Deuda conocida (si amarillo): 
Acción (si rojo): 
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
