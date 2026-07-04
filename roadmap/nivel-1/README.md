# Nivel 1 — Producto de texto, lanzable

> El foco real. Todo lo de esta carpeta es para llevar el firewall de "anda en mi máquina" a "lanzado públicamente con evidencia que se defiende sola".

**Estado (2026-07-04):** etapas **1 y 2 hechas**.

**Trabajo de código activo ahora:** opción A (RAG más rico) en [`../../roadmap.md`](../../roadmap.md).  
**Pendiente de producto y opciones B/C:** [`../../roadmap-backlog.md`](../../roadmap-backlog.md).  
Tras A, el siguiente foco de producto del Nivel 1 sigue siendo la **etapa 3 (UX)**, salvo que se priorice B.

---

## La secuencia (tu roadmap, ordenado)

| # | Etapa | Qué logra | Estado |
|---|-------|-----------|--------|
| 1 | [Estabilización](etapa-1-estabilizacion.md) | Anda sin crashes + higiene de repo (incl. **limpiar datos privados**) | Hecha |
| 2 | [Logging](etapa-2-logging.md) | Trazas confiables, exportables a Graylog/Datadog/estándar | Hecha |
| 3 | [UX / flow](etapa-3-ux.md) | Embellecer y pulir el flujo de usuario | **Siguiente** |
| 4 | [**CHECKPOINT: testeo**](etapa-4-checkpoint-testeo.md) | Parate. ¿Anda sólido? ¿Se ve serio? | Pendiente (⛔ obligatorio) |
| 5 | [Automatización de calibración](etapa-5-automatizacion-calibracion.md) | Harness que encuentra la mejor calibración por corpus | Pendiente |
| 6 | [Auditoría y evidencia](etapa-6-auditoria-evidencia.md) | Usar el harness para generar reportes reproducibles | Pendiente |
| 7 | [Benchmark comparativo](etapa-7-benchmark-comparativo.md) | Mismo dataset vs. Llama Guard / Prompt Guard | Pendiente |
| 8 | [**CHECKPOINT**](etapa-8-checkpoint.md) | Parate. ¿Los números cuentan una historia honesta? | Pendiente (⛔ obligatorio) |
| 9 | [Plan de lanzamiento](etapa-9-plan-lanzamiento.md) | Writeup + secuencia de publicación adaptada a vos | Pendiente |

---

## Definición de "Nivel 1 terminado"

Marcás el Nivel 1 como hecho cuando se cumplen **todas**:

### Base (etapas 1–2) — hecha

- [x] El sistema arranca y corre los flujos normales sin crashear (chat, audit, upload, sniffer, proxy v1).
- [x] La suite de tests pasa entera y sabés qué cubre cada test.
- [x] No hay un solo dato privado en el repo ni en el historial de git.
- [x] Las trazas del sniffer son confiables, completas y exportables a un formato estándar.

### Evidencia y lanzamiento (etapas 3–9) — pendiente

- [ ] Tenés un **dataset etiquetado** (on-corpus que debe pasar / off-corpus + adversarial que debe bloquear).
- [ ] Tenés un **número primario**: la performance de tu claim primario (allowlist) sobre ese dataset, reproducible.
- [ ] Tenés ese mismo número para **al menos un baseline** (Llama Guard 3 o Prompt Guard).
- [ ] Demostraste **determinismo**: el mismo prompt da el mismo score en N corridas en tu máquina.
- [ ] Tenés un **writeup** en inglés con hipótesis / método / resultados / **limitaciones explícitas** / link al repo.
- [ ] Tenés un **plan de publicación** con orden de canales y material listo.

> Nota: la Etapa 3 (UX) y el checkpoint de la Etapa 4 no tienen ítems propios en esta lista, pero **bloquean** el paso a evidencia (5–7). No saltees el checkpoint.

---

## Estimación honesta de esfuerzo

No te voy a mentir con "un fin de semana". En tu realidad (energía intermitente, un hijo, burnout), pensalo en **bloques de micro-sesiones**, no en semanas calendario:

- Etapas 1–2: **hechas** (higiene, tooling, logging).
- Etapa 3 (UX): lo que queda de trabajo "de manos" antes de investigación. Micro-sesiones cortas.
- Etapa 4: una sesión de revisión honesta.
- Etapas 5–7 (la parte de investigación/evidencia): es lo más jugoso y lo más lento. Acá está el valor real. No la apures.
- Etapa 8: una sesión de revisión.
- Etapa 9: redacción. Se puede hacer en pedazos.

**Regla:** si una semana solo podés hacer una micro-sesión, hiciste progreso. El roadmap te espera.
