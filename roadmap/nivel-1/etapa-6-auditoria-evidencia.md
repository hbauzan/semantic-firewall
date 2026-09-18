# Etapa 6 — Auditoría y generación de evidencia

> **Estado: pendiente** (después de la Etapa 5).

> Objetivo: usar el harness validado en la Etapa 5 para **generar reportes reproducibles** de la performance del firewall. Acá convertís "anda" en "acá están los números, reproducilos vos mismo".

---

## Qué es evidencia de verdad (y qué no)

Evidencia que se defiende sola tiene tres propiedades:
1. **Reproducible:** cualquiera con el repo y el dataset obtiene los mismos números.
2. **Honesta:** incluye dónde falla, no solo dónde gana.
3. **Comparable:** tiene una baseline (eso es la Etapa 7).

Un número sin reproducibilidad ni baseline no es evidencia, es marketing. Y la audiencia técnica lo huele.

---

## Tareas

### Bloque A — Determinismo (la base de toda la auditabilidad)
Tu narrativa entera es "auditable y trazable". Eso exige determinismo. Hay que **probarlo**, no asumirlo.
- [x] Embebé el mismo prompt N veces (ej. 100) en tu Mac. Confirmá que el vector es idéntico (o dentro de tolerancia fp). — L01: bit-idéntico en Darwin/arm64/MPS, ver `backend/tests/embedder_determinism_report.md`.
- [x] Confirmá que la decisión PASS/BREACH es estable: mismo prompt + mismo corpus + mismos thresholds = mismo veredicto, siempre. — estable; on-corpus es BREACH estable por excitación (calibración, no jitter).
- [x] Documentá el "fingerprint" del entorno donde es determinista: versión de BGE-M3, `sentence-transformers`, `torch`, device (MPS), precisión. Esto es la semilla de la "firma" del Nivel 3 — anotalo, no lo construyas.
- [x] (Nota honesta) El determinismo **cross-hardware** (otra Mac, una GPU NVIDIA) NO está garantizado y probablemente no se sostenga. Para el Nivel 1 alcanza con determinismo **en tu deployment**. Decilo explícito en el writeup; es una limitación honesta, no una debilidad.

### Bloque B — Reportes reproducibles
- [ ] Para cada corpus: reporte con métricas estándar (precisión, recall, F1, FPR, curva ROC, AUC) sobre el dataset etiquetado.
- [ ] Reporte específico del claim primario: **tasa de bloqueo de off-topic con bajo falso-positivo sobre queries legítimas** (la allowlist funcionando).
- [ ] Reporte del claim secundario: **tasa de bloqueo de piggybacking** vs. un firewall que no segmenta (podés simular "no segmentar" evaluando el prompt entero como una sola cláusula).
- [ ] Reporte del número de Etapa 5: aporte de la excitación sobre el coseno.
- [ ] Todo con seed fija, dataset versionado, comando exacto para reproducir. Generá los reportes como Markdown + CSV (reusá el patrón de `metrics_report.csv` y `db_scaling_metrics.md`).

### Bloque C — Paquete forense
- [ ] Que `GET /system/logs/export` (de Etapa 2) produzca un paquete que demuestre la trazabilidad: para una corrida del dataset, cada decisión con su métrica. Esto es lo que un auditor PCI querría ver.
- [ ] Generá un ejemplo de paquete forense "lindo" para mostrar en el writeup.

---

## Definición de "Etapa 6 terminada"
- [x] Determinismo probado y documentado (con fingerprint de entorno y la limitación cross-hardware explícita).
- [ ] Reportes reproducibles para ≥2 corpus, con métricas estándar.
- [ ] Claim primario y secundario cuantificados.
- [ ] Comando exacto + dataset versionado para que cualquiera reproduzca.
- [ ] Paquete forense de ejemplo listo.

---

## Trampas
- **No cherry-piquees.** Si un corpus da peor, reportá los dos. La honestidad es tu escudo: si vos mostrás las debilidades primero, le sacás la munición al crítico.
- **No confundas "lo corrí una vez" con "es reproducible".** Reproducible = seed fija + dataset versionado + comando documentado. Probalo borrando todo y corriendo de cero.
- **El determinismo fp puede tener ruido mínimo.** Definí una tolerancia explícita y documentala; no pretendas igualdad bit a bit si el hardware no la da.

---

## Presupuesto de energía
- Bloque A: 1 micro-sesión (el test de determinismo es corto pero importante).
- Bloque B: 2-3 micro-sesiones (correr + redactar reportes).
- Bloque C: 1 micro-sesión.

---

## Prompts sugeridos

**Test de determinismo:**
```
Leé roadmap/nivel-1/etapa-6-auditoria-evidencia.md, Bloque A. Escribí un script
que embeba el mismo prompt 100 veces y confirme que el vector y el veredicto
PASS/BREACH son estables. Documentá el fingerprint del entorno (versiones de
modelo, sentence-transformers, torch, device). Reportame si hay ruido fp y de
qué magnitud.
```

**Generar reportes reproducibles:**
```
Leé roadmap/nivel-1/etapa-6-auditoria-evidencia.md, Bloque B. Con el harness de
la Etapa 5 y el dataset etiquetado, generá un reporte reproducible (Markdown +
CSV) con precisión/recall/F1/FPR/ROC/AUC para el corpus [X], más el claim
primario (allowlist) y el secundario (piggybacking). Seed fija, comando
documentado. Incluí los casos donde el firewall falla, no solo donde gana.
```
