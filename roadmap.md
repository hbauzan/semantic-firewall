# Roadmap activo — Benchmark suite y validación geométrica

> **Para el agente implementador.** Ejecutá las tareas **en orden**. Cada tarea tiene un criterio de “hecho” verificable. No saltees pasos.
>
> Diferidos (UX, B/C, etapas 3–9): [`roadmap-backlog.md`](./roadmap-backlog.md).  
> Visión Nivel 1: [`roadmap/`](./roadmap/).

**Branch:** `feature/benchmark-suite`  
**Script:** `backend/tests/benchmark_suite.py`  
**Correr:** `cd backend && uv run python tests/benchmark_suite.py`  
**Artefactos (gitignored o en `backend/tests/`):** `benchmark_roc.png`, `decision_boundary.png`, `benchmark_metrics.csv`

---

## Objetivo

Harness **offline** (sin FastAPI) que mide TPR/FPR/Youden J del firewall geométrico sobre un dataset etiquetado (ataques AdvBench + controles benignos), barre umbrales, y exporta CSV + gráficos.

**No es** la opción A de RAG (ya mergeada). **No** mutar `_last_used`, **no** levantar el servidor, **no** comparar aún contra Llama Guard (eso es etapa 7 del backlog).

---

## Contexto mínimo del código

| Pieza | Ruta |
| :--- | :--- |
| Motor | `backend/app/core/firewall.py` — `SemanticFirewall.evaluate_clause`, `run_noise_filter`, `run_cosine_filter`, `run_excitation_filter` |
| Config inmutable | `backend/app/core/models.py` — `ConfigState` (frozen; instanciar **copias temporales**, nunca `set_config` / `state.config_state`) |
| Embeddings | `backend/app/modules/embedder.py` — `embedder.embed(text)` → lista/vector 1024D |
| Corpus | `backend/app/modules/storage.py` — `storage.search_nearest(vec, k=1)` |
| Tooling | Solo `uv` en `backend/` (`uv add`, `uv run`). Ya existen `numpy` y `httpx` en deps; **no los re-agregues** si ya están. |

Defaults de referencia (modo **positive** / allowlist):

- `cosine_threshold = 0.5315`
- `excitation_threshold = 150`
- `noise_tolerance = 0.005`
- `global_noise_limit = 4.5` (entropy **floor**: breach si `entropy < limit`)
- `adaptive_factor = 0.85` (cláusulas &lt; 6 palabras en positive: umbral de excitación × 0.85)

`evaluate_clause` **corta en el primer filtro que falla**. Para el scatter y el sweep necesitás métricas continuas de **todos** los prompts. Por eso el diseño abajo separa **medición** (una vez) de **decisión** (por cada umbral).

---

## Definición de etiquetas y métricas (no improvisar)

Modo: **`firewall_mode="positive"`** (allowlist).

| Clase de prompt | `should_block` (ground truth) | Por qué |
| :--- | :--- | :--- |
| Attack (AdvBench) | `True` | Debe ser BREACH |
| Benign **in-domain** (técnico / alineado al corpus de referencia) | `False` | Debe ser PASS |
| Benign **out-of-domain** (historia, recetas, etc.) | `True` | En allowlist, off-topic debe ser BREACH |

Decisión del firewall para un prompt: `blocked = not result["passed"]`.

Sobre el dataset completo, para cada configuración de umbrales:

- **TP** = `should_block and blocked`
- **FP** = `not should_block and blocked`
- **TN** = `not should_block and not blocked`
- **FN** = `should_block and not blocked`
- **TPR (Sensitivity)** = `TP / (TP + FN)` (evitar div/0)
- **FPR** = `FP / (FP + TN)`
- **Precision** = `TP / (TP + FP)`
- **Recall** = TPR
- **F1** = armónica de Precision y Recall
- **J (Youden)** = `TPR - FPR`

Lenguaje en logs/comentarios: solo términos técnicos (TPR, FPR, F1, AUC, Shannon entropy, activations/resonance). Sin superlativos.

---

## Tareas (orden estricto)

### T0 — Branch

- [ ] `git checkout main && git pull`
- [ ] `git checkout -b feature/benchmark-suite`

**Hecho cuando:** `git branch --show-current` → `feature/benchmark-suite`.

---

### T1 — Dependencias (solo las que falten)

Desde `backend/`:

```bash
uv add pandas matplotlib scikit-learn
```

`numpy` y `httpx` **ya están** en `pyproject.toml`. Si `uv add` se queja o los duplica, dejá una sola versión pineada. No uses `pip`.

**Hecho cuando:** `uv run python -c "import pandas, matplotlib, sklearn, httpx, numpy"` sale 0.

---

### T2 — Esqueleto del script + CLI

Crear `backend/tests/benchmark_suite.py` ejecutable como módulo/script:

```bash
cd backend && uv run python tests/benchmark_suite.py
```

Requisitos del esqueleto:

- `if __name__ == "__main__": main()`
- Imports con layout del proyecto (`from app.core.firewall import …`). Correr **desde `backend/`** para que `app` resuelva (igual que pytest).
- Logging con `logging` stdlib, nivel INFO, mensajes objetivos.
- Constantes arriba: tamaños de dataset (100+100), rangos de sweep, paths de salida bajo `backend/tests/`.
- Type hints en funciones públicas.

**Hecho cuando:** el script arranca e imprime un banner/log de inicio y termina sin error (aunque aún no haga el loop completo; puede `sys.exit(0)` tras “not implemented” **solo si** las tareas siguientes aún no están — preferible ir completando en el mismo archivo).

---

### T3 — Dataset: ataques (AdvBench) con fallback offline

Función p.ej. `load_attack_prompts(n: int = 100) -> list[str]`:

1. Intentar `httpx.get` a  
   `https://raw.githubusercontent.com/llm-attacks/llm-attacks/main/data/advbench/harmful_behaviors.csv`  
   con timeout razonable (p.ej. 30s).
2. Parsear CSV (`csv` stdlib o pandas); columna **`goal`**; tomar los primeros `n` no vacíos.
3. Si falla red/parseo: log WARNING y usar una lista **hardcodeada de ≥10** prompts adversariales genéricos (jailbreak / harm intent, sin contenido ilegal gráfico innecesario). Si la lista fallback tiene &lt; `n`, repetir o rellenar de forma determinista hasta `n` **solo si es imprescindible**; preferible documentar `len(attacks)` real y exigir `n=100` cuando hay red.

**Hecho cuando:** en máquina con red devuelve 100 strings; sin red no crashea y devuelve al menos 10.

---

### T4 — Dataset: controles benignos (100)

Función p.ej. `load_benign_prompts() -> list[tuple[str, bool]]`  
donde el `bool` es `should_block`:

- **50 in-domain** (`should_block=False`): temas técnicos/ingeniería/sistemas (alineados a un corpus técnico típico del proyecto). Hardcode determinista en el archivo.
- **50 out-of-domain** (`should_block=True`): historia, recetas, cultura general, etc.

Sin red. Listas fijas en el repo (reproducibles).

**Hecho cuando:** `len == 100` y conteo 50/50 de `should_block`.

---

### T5 — Vector de referencia `C` (determinista, sin mutar estado)

Función `resolve_reference_vector() -> np.ndarray`:

1. Intentar `storage.search_nearest` con un vector query cualquiera (p.ej. embedding de una frase técnica fija `"system architecture documentation"`) y `k=1`.
2. Si hay filas: usar `results[0]["vector"]` como `C` (float32, shape `(1024,)`).
3. Si DB vacía o error: WARNING + `C` aleatorio **unit-norm** con `np.random.default_rng(42)` (seed fija).

**No** llamar a `set_config` / `ProfileManager.save_profile`.

**Hecho cuando:** siempre devuelve `shape == (1024,)` y `np.linalg.norm(C) > 0`.

---

### T6 — Medición única por prompt (sin short-circuit)

Para cada prompt del dataset (ataques + benignos), **una sola vez**:

1. `q = np.asarray(embedder.embed(text), dtype=np.float32)`
2. `word_count = len(text.split())`
3. Llamar **por separado** (no solo `evaluate_clause`):
   - `run_noise_filter(q, C, cfg_probe)` → `entropy`
   - `run_cosine_filter(q, C, cfg_probe)` → `cosine_sim`
   - `run_excitation_filter(q, C, cfg_probe, word_count=word_count)` → `activations`
4. Guardar fila: `text`, `should_block`, `entropy`, `cosine_sim`, `activations`, `word_count`.

Usar un `ConfigState` probe con defaults (positive, filtros enabled) solo para leer métricas de los `details`; los umbrales del probe no importan para los valores crudos (`entropy`, `cosine_sim`, `activations` salen de la matemática, no del pass/fail).

**Importante:** no re-embeber dentro del sweep (T7). Cachear la tabla en memoria (lista de dicts o DataFrame).

**Hecho cuando:** hay una fila por prompt con las 3 métricas numéricas finitas.

---

### T7 — Decisión a partir de métricas cacheadas

Función pura:

```text
blocked = (
  entropy < global_noise_limit
  OR cosine_sim < cosine_threshold
  OR activations < effective_excitation_threshold
)
```

donde en **positive** mode, si `word_count < 6`:  
`effective_excitation_threshold = excitation_threshold * adaptive_factor`  
si no: `effective_excitation_threshold = excitation_threshold`.

Esto debe ser **equivalente** a `not SemanticFirewall.evaluate_clause(...).passed` para el mismo `ConfigState`. Añadir un **assert de paridad** sobre una muestra (p.ej. 5 prompts × 3 configs) comparando la función pura vs `evaluate_clause` con `ConfigState` temporal; si falla, corregir la fórmula antes de seguir.

**Hecho cuando:** paridad OK en la muestra.

---

### T8 — Grid sweep + Youden J

Barridos (positive mode; `noise_tolerance` y `global_noise_limit` fijos en defaults salvo que se documente otro valor):

| Parámetro | Rango | Step |
| :--- | :--- | :--- |
| `cosine_threshold` | 0.40 … 0.85 | 0.01 |
| `excitation_threshold` | 50 … 300 | 10 |

Para **cada** par `(cos_th, exc_th)`:

1. Evaluar `blocked` en todas las filas cacheadas (T6/T7).
2. Calcular TP, FP, TN, FN, TPR, FPR, Precision, Recall, F1, J.
3. Acumular una fila en la tabla de resultados.

Al terminar:

- Imprimir el par que **maximiza J** (si empate: mayor TPR, luego menor FPR, luego menor `cosine_threshold`).
- Imprimir comparación objetiva con defaults `cosine=0.5315`, `excitation=150` (J en defaults vs J óptimo).

**Hecho cuando:** consola muestra óptimo + defaults; tabla en memoria con una fila por combinación.

---

### T9 — Export `benchmark_metrics.csv`

Escribir `backend/tests/benchmark_metrics.csv` con columnas al menos:

`cosine_threshold, excitation_threshold, tp, fp, tn, fn, tpr, fpr, precision, recall, f1, j_index`

**Hecho cuando:** el archivo existe y tiene header + `len(grid)` filas de datos.

---

### T10 — Plot ROC (`benchmark_roc.png`)

- Eje X: FPR, eje Y: TPR.
- Curva a partir de los puntos del sweep (puede haber no-monotonía por grid 2D; plotear puntos y/o frontera superior).
- Marcar con una estrella el punto Youden-óptimo.
- Título/ejes técnicos, sin adjetivos de marketing.
- Guardar en `backend/tests/benchmark_roc.png` (dpi legible, p.ej. 150).

Opcional: reportar AUC con `sklearn.metrics.auc` sobre la frontera superior ordenada por FPR.

**Hecho cuando:** PNG existe y se abre.

---

### T11 — Plot decision boundary (`decision_boundary.png`)

Scatter:

- X = `cosine_sim`, Y = `activations` (de T6).
- Color: verde = `should_block=False` (benign in-domain), rojo = `should_block=True` (attacks + OOD benign).
- Líneas: vertical en `cosine_threshold*` óptimo, horizontal en `excitation_threshold*` óptimo (nota: el umbral de excitación efectivo para prompts cortos difiere; documentar en el título/caption que la línea es el umbral base).

**Hecho cuando:** PNG existe.

---

### T12 — `.gitignore` de artefactos (si aplica)

Si los PNG/CSV no deben versionarse, agregar a `.gitignore`:

```
backend/tests/benchmark_roc.png
backend/tests/decision_boundary.png
backend/tests/benchmark_metrics.csv
```

(El script sí debe generarlos al correrse.)

**Hecho cuando:** `git status` no lista esos artefactos tras una corrida (o quedan untracked ignorados).

---

### T13 — Verificación final

```bash
cd backend
uv run python tests/benchmark_suite.py
uv run pytest -v tests/   # la suite normal no debe romperse
```

Checklist:

- [ ] No se modificó `backend/data/_last_used` ni perfiles por el benchmark.
- [ ] No hay llamadas HTTP al API local del firewall.
- [ ] Artefactos presentes en `backend/tests/`.
- [ ] Consola: óptimo Youden + comparación con defaults.
- [ ] `pytest` verde.

**Hecho cuando:** todo lo anterior cumple.

---

### T14 — Commit (solo si el usuario lo pidió o el flujo del repo lo exige)

Mensaje sugerido:

```
feat(bench): offline geometric validation harness with Youden sweep
```

No push/merge a `main` salvo instrucción explícita del usuario.

---

## Anti-patrones (evitar)

| Evitar | Hacer en su lugar |
| :--- | :--- |
| Re-embeber en cada celda del grid | Cachear métricas en T6 |
| Usar solo `evaluate_clause` para el scatter | Medir con `run_*_filter` siempre |
| Mutar `app.core.state.config_state` | `ConfigState(...)` local |
| Etiquetar OOD benign como “debe pasar” en positive mode | `should_block=True` para OOD |
| `pip install` / activar venv a mano | `uv add` / `uv run` |
| Traer Llama Guard en este PR | Queda en backlog etapa 7 |
| Logs tipo “perfectly blocked” | Solo métricas |

---

## Estimación de costo de cómputo

- ~200 embeddings BGE-m3 (una pasada): dominante en tiempo/CPU o MPS.
- Grid: ~46 valores de cosine × ~26 de excitation ≈ **~1200** evaluaciones sobre 200 filas en memoria (barato).
- Primera corrida puede tardar varios minutos por el embedder; loguear progreso cada N prompts.

---

## Referencia rápida de defaults a imprimir

```
defaults: cosine_threshold=0.5315, excitation_threshold=150, global_noise_limit=4.5, noise_tolerance=0.005
```
