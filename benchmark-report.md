# Reporte — Benchmark Suite de Validación Geométrica

**Proyecto:** Three-Headed Semantic Firewall (`semantic-firewall`)  
**Fecha de corrida:** 2026-07-04  
**Branch:** `feature/benchmark-suite`  
**Commit:** `66a7f0f` — `feat(bench): offline geometric validation harness with Youden sweep`  
**Script:** `backend/tests/benchmark_suite.py`  
**Comando:** `cd backend && uv run python tests/benchmark_suite.py`

---

## 1. Resumen ejecutivo

Se implementó y ejecutó un harness **offline** que mide el firewall geométrico en modo **positive** (allowlist) sobre 200 prompts etiquetados: 100 ataques AdvBench + 50 benignos in-domain + 50 benignos out-of-domain (OOD).

**Resultado principal:** en la configuración actual del corpus de referencia y el barrido de umbrales definido en el roadmap, **ninguna combinación del grid produce verdaderos negativos** (`tn = 0` en las 1.196 configuraciones). Por eso **Youden J = 0 en todo el barrido** y no hay separación útil entre clases con los rangos probados.

**Causa raíz identificada:** el filtro de **coseno** domina la decisión. El `cosine_sim` máximo observado en todo el dataset es **0.383**, pero el barrido empieza en `cosine_threshold = 0.40`. Con cualquier umbral del grid, **los 200 prompts fallan el filtro de coseno** antes de que excitación o ruido puedan discriminar.

Adicionalmente, el vector de referencia `C` se resolvió desde un chunk del corpus local (manual de **sistema de audio** en español), no desde documentación técnica en inglés alineada a los prompts benignos in-domain del benchmark.

La suite de regresión `pytest` quedó **verde (56/56)**. El harness cumple paridad con `evaluate_clause` y genera los artefactos esperados.

---

## 2. Alcance de las pruebas

### 2.1 Tareas del roadmap ejecutadas (T0–T13)

| Tarea | Descripción | Estado |
| :--- | :--- | :--- |
| T0 | Branch `feature/benchmark-suite` desde `main` | Hecho |
| T1 | Deps: `pandas`, `matplotlib`, `scikit-learn` vía `uv add` | Hecho |
| T2 | Esqueleto `benchmark_suite.py` + CLI | Hecho |
| T3 | AdvBench (100) con fallback offline | Hecho |
| T4 | Benignos 50 in-domain + 50 OOD | Hecho |
| T5 | Vector `C` sin mutar estado | Hecho |
| T6 | Medición única por prompt (`run_*_filter`) | Hecho |
| T7 | Decisión pura + assert de paridad | Hecho |
| T8 | Grid sweep + Youden J | Hecho |
| T9 | Export `benchmark_metrics.csv` | Hecho |
| T10 | Plot `benchmark_roc.png` | Hecho |
| T11 | Plot `decision_boundary.png` | Hecho |
| T12 | `.gitignore` de artefactos | Hecho |
| T13 | Corrida completa + `pytest` | Hecho |
| T14 | Commit en branch del roadmap | Hecho (`66a7f0f`) |

### 2.2 Fuera de alcance (no ejecutado)

- Opción A de RAG, opciones B/C de corpus session/cache
- Comparación con Llama Guard
- Filtrado de salida del LLM
- Levantar FastAPI / llamadas HTTP al API local

### 2.3 Anti-patrones respetados

| Evitado | Cumplido |
| :--- | :--- |
| Re-embeber en cada celda del grid | Métricas cacheadas una vez (T6) |
| Usar solo `evaluate_clause` para medir | `run_noise_filter`, `run_cosine_filter`, `run_excitation_filter` por separado |
| Mutar `config_state` / `_last_used` | `ConfigState` local; sin `set_config` |
| OOD benign como `should_block=False` | OOD etiquetado `should_block=True` |
| `pip` / venv manual | Solo `uv run` |

---

## 3. Configuración del experimento

### 3.1 Modo y defaults del firewall

| Parámetro | Valor |
| :--- | ---: |
| `firewall_mode` | `positive` (allowlist) |
| `cosine_threshold` (default) | 0.5315 |
| `excitation_threshold` (default) | 150 |
| `global_noise_limit` | 4.5 |
| `noise_tolerance` | 0.005 |
| `adaptive_factor` | 0.85 |
| Filtros habilitados | noise, cosine, excitation |

### 3.2 Modelo y corpus

| Componente | Valor |
| :--- | :--- |
| Embedder | `BAAI/bge-m3` (1024D) |
| Filas en LanceDB (`knowledge`) | 1.071 |
| Query para resolver `C` | `"system architecture documentation"` |
| Origen de `C` | `storage.search_nearest(k=1)` → chunk más cercano del corpus |
| Texto del chunk de referencia (inicio) | `Sistema de audio` — manual en español |
| Norma de `C` | 1.0 |

### 3.3 Grid de barrido (T8)

| Parámetro | Rango | Step | Valores |
| :--- | :--- | ---: | ---: |
| `cosine_threshold` | 0.40 … 0.85 | 0.01 | 46 |
| `excitation_threshold` | 50 … 300 | 10 | 26 |
| **Total combinaciones** | | | **1.196** |

`noise_tolerance` y `global_noise_limit` fijos en defaults durante todo el sweep.

### 3.4 Definición de etiquetas (ground truth)

| Clase | N | `should_block` | Criterio esperado |
| :--- | ---: | :--- | :--- |
| Ataques AdvBench | 100 | `True` | Debe ser BREACH |
| Benign in-domain (técnico/ingeniería) | 50 | `False` | Debe ser PASS |
| Benign OOD (historia, recetas, cultura) | 50 | `True` | Debe ser BREACH (off-topic en allowlist) |
| **Total** | **200** | 150 bloqueables / 50 permitibles | |

Decisión medida: `blocked = not result["passed"]`.

---

## 4. Dataset

### 4.1 Ataques (AdvBench)

- **Fuente:** `https://raw.githubusercontent.com/llm-attacks/llm-attacks/main/data/advbench/harmful_behaviors.csv`
- **Columna:** `goal`
- **Cargados:** 100 prompts (HTTP 200 OK)
- **Fallback offline:** lista hardcodeada de ≥15 prompts (no usada en esta corrida)

### 4.2 Benignos

- **In-domain:** 50 prompts técnicos en inglés (TCP/UDP, OAuth, Kubernetes, etc.) — hardcodeados en `benchmark_suite.py`
- **OOD:** 50 prompts de historia, cocina, cultura general — hardcodeados
- **Sin red** para benignos

### 4.3 Costo de cómputo observado

| Fase | Duración aprox. |
| :--- | :--- |
| Carga embedder BGE-m3 | ~10 s (primera corrida) |
| 200 embeddings individuales | ~7 s |
| Grid 1.196 × 200 filas en memoria | < 1 s |
| Generación PNG + CSV | ~2 s |
| **Total corrida benchmark** | **~20 s** (con modelo ya en caché) |

---

## 5. Verificaciones de integridad

### 5.1 Paridad `decide_blocked` ↔ `evaluate_clause` (T7)

- **Muestra:** 5 prompts × 3 configuraciones de umbrales = 15 comparaciones
- **Resultado:** **15/15 coincidencias** (0 mismatches)
- Configs probadas: `(cos=0.50, exc=100)`, defaults `(0.5315, 150)`, `(cos=0.70, exc=200)`

### 5.2 Regresión `pytest` (T13)

```
56 passed, 1 warning in ~2 s
```

- Warning no relacionado: deprecación `httpx` en `starlette.testclient`
- Ningún test existente roto por el harness

### 5.3 Estado del sistema tras el benchmark

| Verificación | Resultado |
| :--- | :--- |
| `_last_used` / perfiles mutados | No |
| Llamadas HTTP al API local | No |
| Artefactos generados | Sí (ver §9) |
| Artefactos versionados en git | No (gitignored) |

---

## 6. Distribución de métricas por clase (medición T6)

Valores continuos medidos **una vez** por prompt con `run_*_filter` (sin short-circuit del pipeline).

### 6.1 Shannon entropy

| Clase | min | max | media | mediana |
| :--- | ---: | ---: | ---: | ---: |
| Ataques (n=100) | 9.5268 | 9.6099 | 9.5649 | 9.5640 |
| In-domain (n=50) | 9.5299 | 9.5982 | 9.5629 | 9.5616 |
| OOD (n=50) | 9.5187 | 9.5909 | 9.5593 | 9.5602 |

- **Umbral de ruido:** `global_noise_limit = 4.5`
- **Prompts con `entropy < 4.5`:** **0 / 200**
- El filtro de ruido **no contribuyó** a ningún bloqueo en este dataset.

### 6.2 Cosine similarity (`cosine_sim`)

| Clase | min | max | media | mediana |
| :--- | ---: | ---: | ---: | ---: |
| Ataques | 0.1769 | **0.3830** | 0.2880 | 0.2875 |
| In-domain | 0.2321 | **0.3752** | 0.2950 | 0.2965 |
| OOD | 0.0333 | 0.2877 | 0.1853 | 0.1907 |

**Observación crítica:** el máximo global de `cosine_sim` es **0.3830** (un ataque AdvBench). El mínimo del grid es **0.40**. Por lo tanto, **en ningún punto del barrido un prompt puede pasar el filtro de coseno**.

Solapamiento ataques vs in-domain: las distribuciones se superponen casi por completo (ataques: media 0.288, in-domain: media 0.295). OOD queda más bajo (media 0.185).

### 6.3 Activations (dimensional resonance)

| Clase | min | max | media | mediana |
| :--- | ---: | ---: | ---: | ---: |
| Ataques | 90 | 147 | 112.31 | 112.5 |
| In-domain | 89 | 136 | 112.96 | 112.5 |
| OOD | 79 | 129 | 105.14 | 105.0 |

- Prompts cortos (`word_count < 6`): **2 / 200** (ambos OOD, `should_block=True`)
- Umbral efectivo de excitación para cortos: `excitation_threshold × 0.85`

### 6.4 Word count

| Clase | min | max | media | mediana |
| :--- | ---: | ---: | ---: | ---: |
| Ataques | 6 | 20 | 12.02 | 12 |
| In-domain | 7 | 13 | 10.00 | 10 |
| OOD | 5 | 12 | 8.98 | 9 |

---

## 7. Comportamiento a umbrales por defecto

Con `cosine_threshold=0.5315`, `excitation_threshold=150`, `global_noise_limit=4.5`:

| Métrica de fallo | Prompts afectados |
| :--- | ---: |
| `entropy < 4.5` | 0 / 200 |
| `cosine_sim < 0.5315` | **200 / 200** |
| `activations < umbral_efectivo` | **200 / 200** |

### Matriz de confusión (defaults)

| | Predicho BLOCK | Predicho PASS |
| :--- | ---: | ---: |
| **should_block=True** (150) | TP = **150** | FN = **0** |
| **should_block=False** (50) | FP = **50** | TN = **0** |

| Métrica | Valor |
| :--- | ---: |
| TPR (Sensitivity / Recall) | 1.0000 |
| FPR | 1.0000 |
| Precision | 0.7500 |
| F1 | 0.8571 |
| **Youden J (TPR − FPR)** | **0.0000** |

### Desglose por subclase (defaults)

| Subclase | Bloqueados | Total | Tasa |
| :--- | ---: | ---: | ---: |
| Ataques | 100 | 100 | 100% |
| Benign in-domain | 50 | 50 | 100% (todos FP) |
| Benign OOD | 50 | 50 | 100% |

---

## 8. Resultados del grid sweep (T8)

### 8.1 Resumen del barrido completo

| Estadística | Valor |
| :--- | ---: |
| Filas en `benchmark_metrics.csv` | 1.196 |
| Matrices de confusión únicas | **1** |
| Configuraciones con `tn > 0` | **0** |
| Configuraciones con `J > 0` | **0** |
| `J` mínimo / máximo | 0.0 / 0.0 |

**Única matriz de confusión en todo el grid:**

| TP | FP | TN | FN |
| ---: | ---: | ---: | ---: |
| 150 | 50 | 0 | 0 |

Esto se repite para **todas** las 1.196 combinaciones `(cosine_threshold, excitation_threshold)`.

### 8.2 Punto Youden-óptimo (criterio del roadmap)

Criterio de desempate: mayor J → mayor TPR → menor FPR → menor `cosine_threshold`.

| Parámetro | Youden óptimo | Defaults |
| :--- | ---: | ---: |
| `cosine_threshold` | **0.4000** | 0.5315 |
| `excitation_threshold` | **50** | 150 |
| TP | 150 | 150 |
| FP | 50 | 50 |
| TN | 0 | 0 |
| FN | 0 | 0 |
| TPR | 1.0000 | 1.0000 |
| FPR | 1.0000 | 1.0000 |
| Precision | 0.7500 | 0.7500 |
| F1 | 0.8571 | 0.8571 |
| **J** | **0.0000** | **0.0000** |
| **ΔJ (óptimo − defaults)** | **0.0000** | — |

El “óptimo” es artefacto del empate: al no existir configuración con `tn > 0`, cualquier punto con TPR=1 y FPR=1 tiene J=0; gana el más permisivo del grid.

### 8.3 Sensibilidad dentro del grid

- A `cosine_threshold = 0.40`, variar `excitation_threshold` de 50 a 300: **misma matriz de confusión**
- A `excitation_threshold = 50`, variar `cosine_threshold` de 0.40 a 0.85: **misma matriz de confusión**

El barrido 2D no produce curva ROC informativa: todos los puntos colapsan en **(FPR=1, TPR=1)**.

### 8.4 AUC

- Frontera superior ROC: un solo punto `(0,0)` → `(1,1)` degenerada
- **AUC (envelope):** no calculable de forma significativa (NaN / degenerado)

---

## 9. Análisis fuera del grid (hallazgo adicional)

Para entender si **algún** umbral podría separar clases, se evaluaron umbrales hipotéticos sobre las métricas cacheadas (no forman parte del sweep del roadmap).

### 9.1 Solo filtro de coseno

| `cosine_threshold` | In-domain PASS | Ataques PASS | OOD PASS |
| :--- | ---: | ---: | ---: |
| ≥ 0.35 | 4 / 50 | 10 / 100 | 0 / 50 |
| ≥ 0.38 | 0 / 50 | 1 / 100 | 0 / 50 |
| ≥ 0.39 | 0 / 50 | 0 / 100 | 0 / 50 |
| ≥ 0.40 (mín. grid) | 0 / 50 | 0 / 100 | 0 / 50 |
| ≥ 0.5315 (default) | 0 / 50 | 0 / 100 | 0 / 50 |

Incluso con umbral muy bajo (0.35), la separación es pobre: pasan 4 in-domain y 10 ataques.

### 9.2 Solo filtro de excitación (sin coseno ni ruido)

| `excitation_threshold` | In-domain blocked | Ataques blocked | OOD blocked |
| :--- | ---: | ---: | ---: |
| 50 | 0 / 50 | 0 / 100 | 0 / 50 |
| 90 | 1 / 50 | 0 / 100 | 3 / 50 |
| 100 | 3 / 50 | 14 / 100 | 9 / 50 |
| 110 | 15 / 50 | 41 / 100 | 31 / 50 |
| 120 | 38 / 50 | 80 / 100 | 49 / 50 |
| 130 | 49 / 50 | 94 / 100 | 50 / 50 |
| 150 (default) | 50 / 50 | 100 / 100 | 50 / 50 |

La excitación **sí** tiene poder discriminativo parcial si el coseno no bloquea todo primero. A `exc=110` hay separación imperfecta pero no nula. En el pipeline real con los tres filtros activos, el coseno impide llegar a ese régimen con el `C` actual.

---

## 10. Artefactos generados

| Archivo | Ruta | Tamaño | Git |
| :--- | :--- | ---: | :--- |
| Métricas CSV | `backend/tests/benchmark_metrics.csv` | 71 KB | Ignorado |
| Curva ROC | `backend/tests/benchmark_roc.png` | 45 KB | Ignorado |
| Frontera de decisión | `backend/tests/decision_boundary.png` | 82 KB | Ignorado |
| Script harness | `backend/tests/benchmark_suite.py` | 28 KB | Versionado |

Columnas del CSV:  
`cosine_threshold, excitation_threshold, tp, fp, tn, fn, tpr, fpr, precision, recall, f1, j_index`

---

## 11. Hallazgos

### H1 — El grid de coseno no alcanza el rango donde hay señal

El `cosine_sim` máximo del dataset (0.383) está **por debajo** del mínimo barrido (0.40). El sweep no puede encontrar configuraciones donde los in-domain pasen; J queda en 0 por construcción del rango, no por un bug del harness.

### H2 — Desalineación corpus ↔ prompts del benchmark

`C` proviene de un chunk en español sobre **sistema de audio** del vehículo, mientras los prompts in-domain del benchmark están en **inglés técnico genérico** (redes, bases de datos, cloud). Los cosenos quedan bajos para todas las clases (~0.18–0.38), con fuerte solapamiento entre ataques e in-domain.

### H3 — El filtro de ruido no discrimina en este dataset

Todas las entropías ~9.52–9.61, muy por encima del piso 4.5. Ningún prompt activa burst detection.

### H4 — La excitación tiene señal latente no explotable con el pipeline actual

Distribuciones de `activations` difieren entre OOD (más bajas) y el resto, pero con defaults ambos filtros (coseno + excitación) bloquean el 100% de los prompts.

### H5 — El harness funciona según especificación

- Paridad con `evaluate_clause` verificada
- 200 embeddings, cache en memoria, sweep barato
- Artefactos y logs generados
- `pytest` verde

### H6 — Métricas reportadas con TPR=FPR=1 no implican firewall “perfecto”

TPR=1 porque todos los `should_block=True` quedan bloqueados. FPR=1 porque **todos** los in-domain también quedan bloqueados. Precision=0.75 es solo `150/(150+50)` — la mitad de lo bloqueado es ground-truth correcto, la otra mitad son falsos positivos in-domain.

---

## 12. Recomendaciones (siguiente iteración)

1. **Alinear `C` con el dominio del benchmark:** usar un chunk técnico en inglés del corpus, o embedder query alineada al dominio real del allowlist (p. ej. documentación de sistemas del proyecto).
2. **Extender el sweep de coseno hacia abajo:** p. ej. 0.20–0.85, para cubrir el rango observado (0.03–0.38).
3. **Repetir el benchmark con el corpus que usará producción**, no solo el chunk más cercano a una frase genérica.
4. **Evaluar umbrales por filtro por separado** antes del sweep conjunto, para ver qué filtro limita.
5. **Considerar métricas por subclase** (ataques vs OOD vs in-domain) en el CSV exportado.

---

## 13. Comandos de reproducción

```bash
# Benchmark completo
cd backend && uv run python tests/benchmark_suite.py

# Regresión
cd backend && uv run pytest -v tests/
```

---

## 14. Referencia rápida de defaults

```
cosine_threshold=0.5315
excitation_threshold=150
global_noise_limit=4.5
noise_tolerance=0.005
adaptive_factor=0.85
firewall_mode=positive
```

---

*Reporte generado a partir de la corrida del 2026-07-04 en `feature/benchmark-suite` (`66a7f0f`). Los artefactos PNG/CSV viven en `backend/tests/` y están en `.gitignore`.*
