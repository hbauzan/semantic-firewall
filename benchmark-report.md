# Reporte — Benchmark Suite de Validación Geométrica (Prisma ES)

**Proyecto:** Three-Headed Semantic Firewall (`semantic-firewall`)  
**Fecha de corrida:** 2026-07-04 (realineación Prisma)  
**Branch:** `feature/benchmark-suite`  
**Script:** `backend/tests/benchmark_suite.py`  
**Comando:** `cd backend && uv run python tests/benchmark_suite.py`

---

## 1. Resumen ejecutivo

Se realineó el harness offline al manual **Chevrolet Prisma 2016 (ES)** con:

- Calibración previa del pack (`calibrate_positive_for_pack`)
- Retrieval acotado: `search_nearest_for_pack` → `om_ng-chevrolet_Prisma_my15-es_AR.pdf.pdf`
- Segmentación multi-cláusula (paridad `/chat`)
- Dataset **215 prompts**: 50 in-domain Prisma ES + 50 OOD + 100 AdvBench + 15 GCG textual
- Grid: cosine 0.20–0.85 (step 0.01) × excitation 50–300 (step 10) → **1.716 configs**

**Resultado principal:** separación útil recuperada. **Youden J máximo = 0.9297** (cos=0.51, exc=50). **808/1716** configs con `tn > 0`. In-domain Prisma: **96%** con `cosine_sim ≥ 0.50`.

La corrida anterior (inglés IT vs chunk “sistema de audio”) tenía J=0 en todo el grid; ver sección 12.

**pytest:** 75 passed.

---

## 2. Pipeline de filtros (orden de ejecución)

### Producción y paridad (`evaluate_clause`, `/chat`, calibración)

Orden por defecto en `ConfigState` (`backend/app/core/models.py`):

| Orden | Filtro | Campo |
| ---: | :--- | :--- |
| **1** | **Noise** (Shannon entropy floor) | `noise_order=1` |
| **2** | **Cosine** (similitud coseno Q↔C) | `cosine_order=2` |
| **3** | **Excitation** (dimensional resonance) | `excitation_order=3` |

`SemanticFirewall.build_pipeline()` ordena por esos valores y **corta en el primer fallo** (short-circuit). En modo **positive**, el primer filtro que no pasa determina `breach_reason` (`noise`, `cosine` o `excitation`).

La calibración usa el snapshot de config viva (`config_state`) incluyendo orden y toggles ON/OFF del HUD.

### Medición en benchmark (T6) y sweep (T7)

Para el grid Youden, el harness **no** short-circuita:

1. Mide **los tres filtros por separado** por cláusula (`run_noise_filter`, `run_cosine_filter`, `run_excitation_filter`).
2. Decisión cacheada: `blocked = (entropy < limit) OR (cosine < th) OR (activations < exc_eff)` por cláusula; prompt bloqueado si **cualquier** cláusula falla.

Esa lógica OR es **equivalente** a `not evaluate_clause(...).passed` en positive mode con los tres filtros habilitados (paridad verificada: 18/18 checks).

---

## 3. Flujo de la corrida

```
1. calibrate_positive_for_pack(Prisma)  → umbrales Youden sobre ~26 queries auto
2. build_dataset()                      → 215 prompts etiquetados
3. measure_dataset()                    → embed + pack-scoped C por cláusula
4. run_sweep()                          → 1.716 configs, noise_limit = post-Cal
5. export CSV + ROC + decision boundary
```

---

## 4. Calibración previa (pack Prisma)

| Campo | Valor |
| :--- | ---: |
| Pack | `om_ng-chevrolet_Prisma_my15-es_AR.pdf.pdf` |
| Chunks LanceDB | 903 |
| Dataset | `auto_om_ng_chevrolet_prisma_my15_es_ar.json` (gitignored) |
| Generación | LLM (`generation_method=llm`) |
| `cosine_threshold` | **0.4800** |
| `excitation_threshold` | **250** |
| `global_noise_limit` | **1.5** |
| Accuracy dataset Cal | **100%** |

La calibración optimiza sobre el dataset auto (~26 queries). El benchmark usa 215 prompts distintos; por eso los umbrales Cal **no** maximizan J en el benchmark (ver §8).

---

## 5. Dataset benchmark (215)

| Clase | N | `should_block` |
| :--- | ---: | :--- |
| Benign in-domain Prisma ES | 50 | `False` |
| Benign OOD | 50 | `True` |
| AdvBench | 100 | `True` |
| GCG textual (ruido) | 15 | `True` |

Retrieval: `storage.search_nearest_for_pack(q, PACK_FILENAME, k=1)` por cláusula.  
Segmentación: `SemanticFirewall.segment()` — una cláusula fallida → prompt bloqueado.

---

## 6. Métricas por clase (peor cláusula por prompt)

| Clase | cosine min | cosine max | cosine mean | entropy range | activations range |
| :--- | ---: | ---: | ---: | :--- | :--- |
| in_domain | 0.454 | **0.740** | 0.634 | 9.53–9.59 | 110–195 |
| ood | 0.218 | 0.500 | 0.370 | 9.52–9.60 | 96–145 |
| advbench | 0.313 | 0.523 | 0.425 | 9.53–9.61 | 101–155 |
| gcg_noise | 0.388 | 0.574 | 0.472 | 9.51–9.57 | 108–145 |

- In-domain con `cosine_sim ≥ 0.50`: **48 / 50 (96%)**
- Cláusulas GCG con `entropy < 4.5`: **0 / 15** (repetición textual no colapsa |embedding| en BGE-m3)

---

## 7. Resultados Youden

### Grid óptimo (benchmark sweep)

| Métrica | Valor |
| :--- | ---: |
| `cosine_threshold` | **0.5100** |
| `excitation_threshold` | **50** |
| **J (Youden)** | **0.9297** |
| TPR | 0.9697 |
| FPR | 0.0400 |
| F1 | 0.9786 |
| TP / FP / TN / FN | 160 / 2 / 48 / 5 |

### HUD defaults (`0.5315 / 150 / 4.5`)

| Métrica | Valor |
| :--- | ---: |
| J | 0.6600 |
| TPR / FPR | 1.0000 / 0.3400 |
| TP / FP / TN / FN | 165 / 17 / 33 / 0 |

### Umbrales calibración pack (`0.48 / 250 / 1.5`)

| Métrica | Valor |
| :--- | ---: |
| J | 0.0000 |
| TPR / FPR | 1.0000 / 1.0000 |
| TP / FP / TN / FN | 165 / 50 / 0 / 0 |

| Comparación | ΔJ |
| :--- | ---: |
| Grid óptimo − Calibración | +0.9297 |
| Grid óptimo − HUD defaults | +0.2697 |

**Configs con tn > 0:** 808 / 1.716

---

## 8. Hallazgos

### H1 — Realineación corpus resolvió J=0

Queries Prisma ES + `C` dinámico por cláusula desde el mismo pack → cosenos in-domain 0.45–0.74 vs 0.23–0.38 en la corrida inglés/audio.

### H2 — Calibración ≠ benchmark

Dataset Cal pequeño y distinto; `exc=250` bloquea todo el benchmark. El grid del benchmark encuentra óptimo local más útil para las 215 queries.

### H3 — Noise filter no ejercitado por GCG textual

Entropía de |Q| ~9.5 en todos los prompts. El filtro de ruido no discrimina en esta corrida; domina coseno/excitación.

### H4 — Paridad multi-cláusula OK

18 comparaciones `decide_blocked_clause` vs `evaluate_clause` sin mismatches.

---

## 9. Artefactos

| Archivo | Filas / tamaño | Git |
| :--- | :--- | :--- |
| `backend/tests/benchmark_metrics.csv` | 1.716 filas | ignorado |
| `backend/tests/benchmark_roc.png` | — | ignorado |
| `backend/tests/decision_boundary.png` | — | ignorado |

---

## 10. Reproducción

```bash
cd backend && uv run python tests/benchmark_suite.py
cd backend && uv run pytest -v tests/
# Omitir calibración:
cd backend && uv run python tests/benchmark_suite.py --skip-calibration
```

---

## 11. Anti-patrones respetados

- No mutar `_last_used` / `config_state` desde el benchmark
- No HTTP al API local
- Métricas cacheadas (no re-embed en grid)
- OOD etiquetado `should_block=True`
- Solo `uv run`

---

## 12. Corrida anterior (referencia — pre-realineación)

| Aspecto | Corrida v1 | Corrida v2 (este reporte) |
| :--- | :--- | :--- |
| In-domain | Inglés IT | Español Prisma |
| Vector C | Global, query fija EN | Por cláusula, pack Prisma |
| N prompts | 200 | 215 |
| cosine max global | 0.383 | 0.740 |
| J máximo grid | 0.0 | **0.9297** |
| tn > 0 en grid | 0 / 1.196 | 808 / 1.716 |

---

*Generado tras corrida 2026-07-04 en `feature/benchmark-suite`.*

---

## Batería de filtros (Prisma, 215 prompts)

Multi-cláusula, pack-scoped C, decisión vía `evaluate_clause` (short-circuit).

### Perfil `hud_defaults`

Umbrales: cosine=0.5315, excitation=150, global_noise_limit=4.5

| Modo | Pipeline | TP | FP | TN | FN | TPR | FPR | F1 | J |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Cosine only | cosine | 162 | 3 | 47 | 3 | 0.9818 | 0.0600 | 0.9818 | 0.9218 |
| Noise only | noise | 0 | 0 | 50 | 165 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Excitation only | excitation | 159 | 16 | 34 | 6 | 0.9636 | 0.3200 | 0.9353 | 0.6436 |
| Cosine → Noise → Excitation | cosine → noise → excitation | 165 | 17 | 33 | 0 | 1.0000 | 0.3400 | 0.9510 | 0.6600 |

### Perfil `grid_optimal_v2`

Umbrales: cosine=0.5100, excitation=50, global_noise_limit=4.5

| Modo | Pipeline | TP | FP | TN | FN | TPR | FPR | F1 | J |
| :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Cosine only | cosine | 160 | 2 | 48 | 5 | 0.9697 | 0.0400 | 0.9786 | 0.9297 |
| Noise only | noise | 0 | 0 | 50 | 165 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Excitation only | excitation | 0 | 0 | 50 | 165 | 0.0000 | 0.0000 | 0.0000 | 0.0000 |
| Cosine → Noise → Excitation | cosine → noise → excitation | 160 | 2 | 48 | 5 | 0.9697 | 0.0400 | 0.9786 | 0.9297 |

### Delta full pipeline vs cosine-only (HUD)

- ΔJ = -0.2618
- ΔTPR = +0.0182
- ΔFPR = +0.2800 (positive = more in-domain false blocks)

