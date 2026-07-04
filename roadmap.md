# Roadmap activo — Opción A: RAG más rico por request

> **Para el agente implementador.** Este archivo es el único trabajo activo ahora.
> Pendientes de producto (UX, evidencia, lanzamiento) y opciones futuras de corpus (sesión B, caché C) están en [`roadmap-backlog.md`](./roadmap-backlog.md).
> El mapa histórico del Nivel 1 sigue en [`roadmap/`](./roadmap/) (etapas 1–2 hechas).

---

## Objetivo

Que el LLM reciba **más texto real del corpus** en cada pregunta que pasa el firewall, sin sesiones ni cachés de provider.

Hoy el modelo solo ve ~`rag_top_k` chunks (default **3**, techo **10**), y el contexto se arma **solo con la primera cláusula** que tiene resultados. Por eso las respuestas suelen ser incompletas aunque el PDF esté indexado.

**Fuera de alcance (no implementar):**

- Sesión con corpus inyectado una vez (opción B) — ver backlog.
- Context caching de Gemini/Anthropic/OpenAI (opción C) — ver backlog.
- Filtrado geométrico de la **salida** del LLM.
- Cambiar la matemática del firewall (sigue evaluando contra el **top-1** vector por cláusula).

---

## Contexto del sistema (imprescindible)

### Qué es

Firewall geométrico delante de un LLM: embebe el prompt (BGE-m3, 1024D), lo segmenta en cláusulas, corre Noise / Cosine / Excitation contra el corpus en LanceDB. **PASS** → se llama al upstream (Ollama, Google, OpenAI, Anthropic, Groq) con un bloque de texto RAG. **BREACH** → no se llama al modelo.

### Cómo se arma el contexto hoy (bug de producto)

Archivo clave: [`backend/app/api/endpoints/chat.py`](backend/app/api/endpoints/chat.py).

```python
# Por cada cláusula:
results = storage.search_nearest(cl_vec, k=cfg.rag_top_k)
# Firewall usa results[0]["vector"] (top-1) — NO CAMBIAR ESO.
if not context:
    # BUG: solo la PRIMERA cláusula con hits llena el context
    context = "\n---\n".join(r["text"] for r in results)
```

Luego `_stream_via_provider(prompt, context, cfg, strict=True)` manda:

```text
Context:
<chunks>
---
<chunks>

User query:
<prompt>
```

El historial en [`backend/app/modules/persistence.py`](backend/app/modules/persistence.py) es **solo UI**; no se reenvía al LLM en `/chat`.

### Proxy `/v1/chat/completions`

Corre el firewall pero **no inyecta RAG**: reenvía `config.messages` tal cual al provider. La opción A se aplica a **`POST /chat`** (HUD) y a **`POST /audit`** / `audit_query` en [`config.py`](backend/app/api/endpoints/config.py) para mantener paridad documentada en `architecture_spec.md`. No hace falta inventar RAG en el proxy en esta tarea (el cliente del proxy trae su propio historial).

### Storage

[`backend/app/modules/storage.py`](backend/app/modules/storage.py) — `search_nearest(query_vector, k)` devuelve filas LanceDB con al menos `text` y `vector`. No hay API de “todos los chunks” necesaria para A.

### Config

| Lugar | Campo | Hoy |
| :--- | :--- | :--- |
| [`backend/app/core/models.py`](backend/app/core/models.py) `ConfigState` / `ConfigUpdate` | `rag_top_k` | default `3`, `ge=1`, `le=10` |
| [`backend/app/core/settings.py`](backend/app/core/settings.py) | `rag_top_k` | mismo (env; el runtime usa `ConfigState`) |
| [`manifest.json`](manifest.json) `state_schema.rag_top_k` | range `[1,10]`, default `3` |
| [`frontend/src/components/ControlPanel.tsx`](frontend/src/components/ControlPanel.tsx) | slider RAG | `min={1} max={10}` |
| Tests | `test_rag_top_k_*` en `test_engine.py`, `test_config_sync_includes_rag_top_k` en `test_api.py` | asumen techo 10 y default 3 |

### Tooling (obligatorio)

- Backend: `uv run` desde `backend/` (nunca `pip` / `source .venv`).
- Frontend: `pnpm`.
- Tests: `cd backend && uv run pytest -v tests/`.
- Doc-sync **condicional** (dev-protocol): actualizar `manifest.json` solo si cambia `state_schema`; `CHANGELOG.md` con una línea de capacidad; `architecture_spec.md` sección RAG; `CONTEXT.md` si cambia la definición de RAG Context; `README.md` solo si documenta el slider/rango.

---

## Requisitos de la opción A

### A1 — Subir techo y default de `rag_top_k`

| Parámetro | Antes | Después (recomendado) |
| :--- | :--- | :--- |
| Default | 3 | **12** |
| Máximo (schema + UI) | 10 | **32** |
| Mínimo | 1 | 1 (sin cambio) |

Actualizar en el mismo cambio: `ConfigState`, `ConfigUpdate`, `settings.rag_top_k` (si aplica), `manifest.json` `state_schema`, slider del Control Panel (`max={32}`), tests de validación (`rag_top_k=0` y `rag_top_k=33` deben fallar; default fresh state `== 12`).

Perfiles `_last_used` con `rag_top_k=3` o `5` siguen válidos (dentro del rango). No migrar perfiles a la fuerza.

### A2 — Contexto multi-cláusula (fix principal)

Mientras se evalúan las cláusulas en `chat_endpoint` (y el camino equivalente de audit):

1. Por cada cláusula con `results` no vacío, **acumular** los textos de esos `results` (no solo la primera cláusula).
2. **Deduplicar** chunks para no repetir el mismo texto si dos cláusulas recuperan el mismo nodo (usar `id` de la fila LanceDB si existe; si no, hash/normalización del `text`).
3. Preservar un orden estable: p.ej. orden de primera aparición al recorrer cláusulas en orden, y dentro de cada cláusula el orden de `search_nearest` (más cercano primero).
4. Unir con el separador existente `"\n---\n"`.
5. El firewall **sigue** usando solo `results[0]` (top-1) para la geometría. No cambiar `evaluate_clause`.

Pseudocódigo orientativo:

```python
context_chunks: list[str] = []
seen_ids: set = set()

for clause in clauses:
    results = storage.search_nearest(cl_vec, k=cfg.rag_top_k)
    if not results:
        # misma lógica no_context / negative que hoy
        ...
        continue

    for row in results:
        key = row.get("id", row["text"])
        if key in seen_ids:
            continue
        seen_ids.add(key)
        context_chunks.append(row["text"])

    # firewall: solo top-1
    db_vec = results[0]["vector"]
    ...

context = "\n---\n".join(context_chunks)
```

Extraer un helper pequeño (p.ej. `_accumulate_rag_context(results, context_chunks, seen_ids)`) si evita duplicar lógica entre `chat_endpoint` y `audit` / proxy-eval loops — preferible un solo lugar.

### A3 — Telemetría visible (chunks inyectados)

En el bloque `[FIREWALL_AUDIT]` que ya emite el chat en PASS, agregar una línea clara, por ejemplo:

```text
RAG: 12 chunks injected (k=12, clauses=2, unique=12)
```

Campos útiles: `k` usado (`cfg.rag_top_k`), número de cláusulas que aportaron hits, número de chunks únicos inyectados.

Opcional pero deseable: incluir en el `pipeline_trace` / evento sniffer un stage o metadata `rag_context` con `chunk_count` (sin volcar el texto completo del corpus al sniffer — solo conteos). No loguear el texto RAG completo en `firewall.log` (puede ser sensible y enorme).

### A4 — Tests

- Actualizar `test_rag_top_k_default` → default 12.
- Actualizar `test_rag_top_k_validation` → rechaza `0` y `33` (o el max+1).
- `test_config_sync_includes_rag_top_k`: aceptar un valor en el nuevo rango (p.ej. 20).
- **Nuevo test** (preferible en `test_api.py` o `test_engine.py` con mocks de storage/embedder): prompt con **dos cláusulas** que recuperarían sets distintos; el context pasado al provider (mockear `stream_chat` o el helper de acumulación) debe contener chunks de **ambas**, sin duplicar el mismo `id`.
- Suite completa verde: `cd backend && uv run pytest -v tests/`.

### A5 — Docs (condicional)

- [`manifest.json`](manifest.json): `state_schema.rag_top_k` default/range.
- [`CHANGELOG.md`](CHANGELOG.md): bullet bajo v2.33.1 o nueva línea de versión patch si preferís bump (si bump: `manifest` + `main.py` version alineados).
- [`architecture_spec.md`](architecture_spec.md): sección RAG — default/techo nuevos; contexto = unión deduplicada de top-K **por cláusula**; firewall sigue en top-1.
- [`CONTEXT.md`](CONTEXT.md): una línea en **RAG Context** — “unión de hasta `rag_top_k` chunks por cláusula, deduplicados”.
- [`README.md`](README.md): solo si menciona el rango 1–10 del slider.

No tocar `roadmap-backlog.md` salvo para marcar A como hecha si el backlog la lista (hoy A está solo aquí).

---

## Criterios de aceptación

- [ ] Default `rag_top_k == 12` en `ConfigState()` fresco.
- [ ] UI permite 1–32; API rechaza fuera de rango.
- [ ] Prompt multi-cláusula PASS inyecta chunks de todas las cláusulas con hits (deduplicados).
- [ ] Firewall sigue bloqueando/pasando igual que antes para el mismo top-1 (no cambiar tests de engine de filtros salvo defaults de k).
- [ ] Telemetría del chat muestra cuántos chunks se inyectaron.
- [ ] `uv run pytest -v tests/` verde.
- [ ] Docs mínimas sincronizadas (manifest + architecture_spec + CONTEXT + CHANGELOG).

---

## Cómo verificar a mano

1. `./run_server.sh` y `./run_ui.sh`.
2. Corpus con un PDF cargado.
3. Control Panel: subir RAG Context Depth a 20, aplicar config.
4. Pregunta que toque **dos temas distintos** del mismo documento (dos cláusulas).
5. En el bloque `[FIREWALL_AUDIT]` debe verse `RAG: N chunks injected` con `N > rag_top_k` si ambas cláusulas aportan chunks distintos (o `N == k` si solo una aporta).
6. La respuesta del LLM debe citar datos de ambas partes del doc con más frecuencia que antes (cualitativo).

---

## Estilo de implementación

- Diff mínimo: no refactors de providers, sniffer ni frontend más allá del slider y el wire de `rag_top_k`.
- Un commit o pocos commits chicos (`fix(rag): …`, `test(rag): …`, `docs(rag): …`).
- Branch sugerida: `feat/rag-richer-context`.
- No commitear `.env`, `backend/data/*.json`, `context.txt`, `_archive/`.

---

## Referencias rápidas

| Tema | Ruta |
| :--- | :--- |
| Chat + RAG + telemetría | `backend/app/api/endpoints/chat.py` |
| Audit paridad | `backend/app/api/endpoints/config.py` |
| Schema | `backend/app/core/models.py` |
| LanceDB | `backend/app/modules/storage.py` |
| Slider UI | `frontend/src/components/ControlPanel.tsx` |
| Spec RAG actual | `architecture_spec.md` (~línea que menciona `rag_top_k`) |
| Glosario | `CONTEXT.md` → RAG Context |
| Backlog (B, C, etapas 3–9) | `roadmap-backlog.md` |
