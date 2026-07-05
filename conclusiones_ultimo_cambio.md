# Conclusiones — Refactor IDS geométrico (2026-07-05)

> Resumen post-implementación del roadmap modular IDS (fases 1–5 del arquitecto, ajustado).
> Branch: merge a `main`. Tests finales: **108 passed**, 3 skipped.

---

## 1. Qué se implementó

El refactor cerró la **infraestructura de medición**, no el claim de producto:

| Fase | Estado | Detalle |
|------|--------|---------|
| **1 — Entropía CPU** | ✅ | `calculate_raw_entropy` + `raw_entropy_limit` (separado de `global_noise_limit`). Logging `SHORT_CIRCUIT layer=raw_entropy`. |
| **2 — RaBitQ + Hamming** | ✅ | Schema LanceDB extendido (`vector_packed`, correcciones RaBitQ, `sparse_lexical` JSON). Prefilter Hamming + SimSIMD opcional. Backfill: `backend/scripts/backfill_sparse_signatures.py`. |
| **3 — MLX nativo** | ⏸ Diferido | Embedder honesto: `st-hybrid-mps|cuda|cpu` vía SentenceTransformer. MLX fusion documentado como trabajo futuro. |
| **4 — Mezcla híbrida** | ✅ | `compute_alpha`, `compute_epsilon` (proxy sintáctico, sin modelo de perplejidad). Sparse short-circuit + hybrid score en `evaluate_clause`. Ingest persiste sparse. |
| **5 — Dispatcher** | ✅ | `UnifiedInferenceDispatcher` con actor thread. Fix deadlock: futures resueltos en el loop que los crea. Test de 20 requests concurrentes. |

### Ajustes deliberados respecto al arquitecto

- **`raw_entropy_limit`** (≈3.0, chars) ≠ **`global_noise_limit`** (≈4.5, vector 1024D).
- **`KnowledgeNode` extendido**, no reemplazado — compatibilidad con calibración e ingest.
- **Perplejidad P(q)** aproximada por longitud + densidad léxica (16GB RAM).
- **SimSIMD** opcional (`uv sync --extra apple`).

---

## 2. El número clave de Etapa 5

Corridas `excitation-compare` post-refactor (datasets v1, corpus demo):

| Corpus | Cosine solo | Cosine + excitación | Rescatados por excitación |
|--------|-------------|---------------------|---------------------------|
| Automotive (25 queries) | 96.0% | 64.0% | **0** |
| Medical (25 queries) | 92.0% | 64.0% | **0** |

Reportes: `backend/calibration/reports/automotive_v1_excitation_compare.md`, `medical_v1_excitation_compare.md`.

### Interpretación honesta

- **Ningún** adversarial/off-topic que el coseno dejaba pasar lo bloquea la excitación.
- El claim *"la excitación cierra la compensación del coseno"* **no se sostiene** con estos datos.
- La excitación **no es redundante de forma inocua**: baja accuracy global (96→64%, 92→64%). Actúa como filtro **más estricto**, con **falsos positivos** sobre queries legítimas, no como red de seguridad adicional sobre fallos del coseno.

---

## 3. Hallazgos técnicos

### Camino híbrido sparse estaba muerto; ahora es medible

Antes `c_sparse` era siempre `None` (ingest solo guardaba dense). Con sparse en LanceDB + backfill, el pipeline híbrido es real. **Aún no hay evidencia** de que sparse aporte sobre dense-only en seguridad — falta experimento explícito.

### Bug de concurrencia corregido

El dispatcher resolvía `asyncio.Future` en el loop del lifespan, no en el de requests async → deadlock en tests (y riesgo en producción). Fix: `future.get_loop().call_soon_threadsafe(...)`.

### Re-ingesta obligatoria

Corpus existente en LanceDB no tiene `sparse_lexical` hasta backfill o re-upload:

```bash
cd backend
uv run python scripts/backfill_sparse_signatures.py --dry-run
uv run python scripts/backfill_sparse_signatures.py
```

### Búsqueda vectorial

Schema con `vector_packed` requiere `vector_column_name="vector"` en búsquedas LanceDB.

---

## 4. Estado del roadmap Nivel 1

| Ítem Etapa 5 | Estado |
|--------------|--------|
| Dataset etiquetado versionado | ✅ v1 automotive + medical |
| Harness calibración (sweep, evaluate, excitation-compare) | ✅ |
| Número "aporte excitación sobre coseno" en ≥2 corpus | ✅ medido = **0** |
| Cambio de frontera óptima entre dominios | ⚠️ pendiente sweep comparativo |

**Etapa 5 no está cerrada en términos de evidencia del claim diferenciador.** Tenés harness + número; el número refuta el titular esperado.

---

## 5. Prioridades siguientes

1. **Diagnosticar el 64%** — `calibration_suite.py evaluate` + revisar mismatches (¿qué on-corpus bloquea excitación?).
2. **Recalibrar `excitation_threshold`** por corpus (sweep Youden) — buscar punto donde excitación no destruya recall.
3. **Expandir dataset** — 25×2 es insuficiente para afirmar/refutar claims; ver `roadmap/nivel-1/etapa-5-automatizacion-calibracion.md`.
4. **Experimento sparse** — cosine vs cosine+sparse vs pipeline completo, con corpus re-ingestado.
5. **Etapa 6** — determinismo + reportes reproducibles antes de confiar en sweep masivo.

---

## 6. Comandos de verificación

```bash
cd backend
uv run pytest -q
uv run python tests/calibration_suite.py evaluate --dataset calibration/datasets/automotive_v1.json
uv run python tests/calibration_suite.py excitation-compare --dataset calibration/datasets/medical_v1.json
uv sync --extra apple   # SimSIMD opcional, Apple Silicon
```

---

## 7. Conclusión en una frase

**La infraestructura IDS quedó lista para hacer ciencia; la ciencia dice que, con lo medido hoy, la excitación no es el titular diferenciador — es un filtro agresivo que hay que recalibrar o repensar antes del writeup de lanzamiento.**
