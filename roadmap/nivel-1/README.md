# Nivel 1 — Producto de texto, lanzable

> El foco real. Todo lo de esta carpeta es para llevar el firewall de "anda en mi máquina" a "lanzado públicamente con evidencia que se defiende sola".

---

## La secuencia (tu roadmap, ordenado)

| # | Etapa | Qué logra | Checkpoint |
|---|-------|-----------|------------|
| 1 | [Estabilización](etapa-1-estabilizacion.md) | Anda sin crashes + higiene de repo (incl. **limpiar datos privados**) | |
| 2 | [Logging](etapa-2-logging.md) | Trazas confiables, exportables a Graylog/Datadog/estándar | |
| 3 | [UX / flow](etapa-3-ux.md) | Embellecer y pulir el flujo de usuario | |
| 4 | [**CHECKPOINT: testeo**](etapa-4-checkpoint-testeo.md) | Parate. ¿Anda sólido? ¿Se ve serio? | ⛔ obligatorio |
| 5 | [Automatización de calibración](etapa-5-automatizacion-calibracion.md) | Harness que encuentra la mejor calibración por corpus | |
| 6 | [Auditoría y evidencia](etapa-6-auditoria-evidencia.md) | Usar el harness para generar reportes reproducibles | |
| 7 | [Benchmark comparativo](etapa-7-benchmark-comparativo.md) | Mismo dataset vs. Llama Guard / Prompt Guard | |
| 8 | [**CHECKPOINT**](etapa-8-checkpoint.md) | Parate. ¿Los números cuentan una historia honesta? | ⛔ obligatorio |
| 9 | [Plan de lanzamiento](etapa-9-plan-lanzamiento.md) | Writeup + secuencia de publicación adaptada a vos | |

---

## Definición de "Nivel 1 terminado"

Marcás el Nivel 1 como hecho cuando se cumplen **todas**:

- [ ] El sistema arranca y corre los flujos normales sin crashear (chat, audit, upload, sniffer, proxy v1).
- [ ] La suite de tests pasa entera y sabés qué cubre cada test.
- [ ] No hay un solo dato privado en el repo ni en el historial de git.
- [ ] Las trazas del sniffer son confiables, completas y exportables a un formato estándar.
- [ ] Tenés un **dataset etiquetado** (on-corpus que debe pasar / off-corpus + adversarial que debe bloquear).
- [ ] Tenés un **número primario**: la performance de tu claim primario (allowlist) sobre ese dataset, reproducible.
- [ ] Tenés ese mismo número para **al menos un baseline** (Llama Guard 3 o Prompt Guard).
- [ ] Demostraste **determinismo**: el mismo prompt da el mismo score en N corridas en tu máquina.
- [ ] Tenés un **writeup** en inglés con hipótesis / método / resultados / **limitaciones explícitas** / link al repo.
- [ ] Tenés un **plan de publicación** con orden de canales y material listo.

---

## Estimación honesta de esfuerzo

No te voy a mentir con "un fin de semana". En tu realidad (energía intermitente, un hijo, burnout), pensalo en **bloques de micro-sesiones**, no en semanas calendario:

- Etapas 1–3 (higiene + estabilización + UX): la mayor parte del trabajo "de manos". Muchas micro-sesiones cortas.
- Etapa 4: una sesión de revisión honesta.
- Etapas 5–7 (la parte de investigación/evidencia): es lo más jugoso y lo más lento. Acá está el valor real. No la apures.
- Etapa 8: una sesión de revisión.
- Etapa 9: redacción. Se puede hacer en pedazos.

**Regla:** si una semana solo podés hacer una micro-sesión, hiciste progreso. El roadmap te espera.
