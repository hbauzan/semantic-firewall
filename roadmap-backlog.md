# Roadmap backlog — trabajo diferido

> Trabajo diferido. **No es un pack tomable de Lxx.**
> L01–L12 cerrado: [`AGENTS.md`](./AGENTS.md), [`roadmap/pilares/README.md`](./roadmap/pilares/README.md).
> Checklist Nivel 1 (fechas 2026-07): [`roadmap.md`](./roadmap.md).
> Detalle: [`roadmap/`](./roadmap/).

Última alineación de estado: **2026-07-04**. Etapas 1–4 del Nivel 1: **hechas** (checkpoint 4 🟡). Etapa 5: **en progreso**.
**Opción A (RAG más rico por request): hecha** — multi-cláusula, `rag_top_k` default 12 / máx 32, telemetría de chunks.

---

## Nivel 1 — pendiente (producto lanzable)

Las etapas detalladas siguen en `roadmap/nivel-1/`. Resumen para no perder el hilo:

| # | Etapa | Archivo | Notas |
|---|-------|---------|--------|
| 3 | UX / flow | [`roadmap/nivel-1/etapa-3-ux.md`](./roadmap/nivel-1/etapa-3-ux.md) | **Hecha** — veredicto legible, demo corpus/queries |
| 4 | Checkpoint testeo | [`roadmap/nivel-1/etapa-4-checkpoint-testeo.md`](./roadmap/nivel-1/etapa-4-checkpoint-testeo.md) | **Hecho 🟡** — load test manual pendiente |
| 5 | Calibración automática | [`roadmap/nivel-1/etapa-5-automatizacion-calibracion.md`](./roadmap/nivel-1/etapa-5-automatizacion-calibracion.md) | **En progreso** — datasets + harness; corridas pendientes |
| 6 | Auditoría / evidencia | [`roadmap/nivel-1/etapa-6-auditoria-evidencia.md`](./roadmap/nivel-1/etapa-6-auditoria-evidencia.md) | Determinismo, reportes reproducibles, paquete forense |
| 7 | Benchmark | [`roadmap/nivel-1/etapa-7-benchmark-comparativo.md`](./roadmap/nivel-1/etapa-7-benchmark-comparativo.md) | vs Llama Guard / Prompt Guard |
| 8 | Checkpoint números | [`roadmap/nivel-1/etapa-8-checkpoint.md`](./roadmap/nivel-1/etapa-8-checkpoint.md) | ¿Historia honesta? |
| 9 | Lanzamiento | [`roadmap/nivel-1/etapa-9-plan-lanzamiento.md`](./roadmap/nivel-1/etapa-9-plan-lanzamiento.md) | Writeup EN + plan de publicación |

Checklist de “Nivel 1 terminado” (ítems aún abiertos): dataset etiquetado, número primario allowlist, baseline, determinismo documentado, writeup, plan de publicación. Ver [`roadmap/nivel-1/README.md`](./roadmap/nivel-1/README.md).

### Ya hecho (no reabrir)

- Etapa 1 — estabilización, `uv`/`pnpm`, datos privados fuera del repo/historial, higiene extra (`_archive/`, manifest slim, `run_pack`).
- Etapa 2 — logging NDJSON, export, resiliencia sniffer.

---

## Nivel 2 — pack de pilares (cerrado)

L01–L12 está en `main` (PRs #4–#15). Registro: [`roadmap/archivo/2026-09-pilares-l01-l12/`](./roadmap/archivo/2026-09-pilares-l01-l12/README.md). Puerta: [`roadmap/pilares/README.md`](./roadmap/pilares/README.md). Visión: [`roadmap/vision/nivel-2.md`](./roadmap/vision/nivel-2.md).

No reabrir Lxx. Cablear lab a prod o A/B cosine es **otro** pack.

## Nivel 3 — visión (no implementar)

- Firmas registrables / certificación: [`roadmap/vision/nivel-3.md`](./roadmap/vision/nivel-3.md).

Regla Nivel 3: no trabajarlo hasta cerrar Nivel 1. El pack de pilares **ya se tomó**; no lo retomes.

---

## Corpus → LLM: opciones diferidas (B y C)

Contexto: el chat no “conoce” el PDF entero. Hoy (y tras la opción A) el modelo recibe solo chunks recuperados por request. A mejora cantidad/calidad del retrieval **sin estado**. B y C atacan “conocer más del corpus” con warm-up o caché de provider.

El firewall **no cambia** en B/C: sigue evaluando cada prompt con embeddings locales; la sesión/caché solo afecta el contexto del LLM **después** del PASS.

### Opción B — Sesión con corpus en historial

**Idea:** en la primera pregunta que pasa el firewall para un par `(upstream_provider, corpus_fingerprint)`, inyectar el corpus (o el máximo que entre en la ventana) **una vez**, avisar en UI/logs (“warming session…”). Preguntas siguientes con el mismo provider y el mismo corpus reutilizan el historial de sesión **sin** reinyectar el bloque grande.

**Invalidar sesión cuando:**

- Cambia `upstream_provider` en el HUD.
- Se sube o borra un pack del corpus.
- El usuario limpia el chat / reset explícito.
- (Opcional) TTL.

**Diseño sugerido:**

- Módulo nuevo p.ej. `backend/app/modules/llm_session.py`: fingerprint (`count_rows` + lista de packs), builder del texto de warm, store en memoria keyed por `(provider, fingerprint)`.
- Prefijo de corpus **inmutable** en la sesión; rotar solo los turnos de chat para no expulsar el corpus de la ventana.
- Si el corpus no entra: truncar con warning claro o fallback a retrieval (opción A).
- Telemetría: `session_warm` | `session_hit` en bloque audit / sniffer (conteos y tokens estimados, no volcar el corpus entero a logs).
- Modo opt-in: p.ej. `rag_mode: retrieval | session` en `ConfigState` (default `retrieval`).
- Empezar solo en `POST /chat` (HUD), no en el proxy `/v1` en el primer corte.

**Velocidad:** primera pregunta lenta; siguientes rápidas. Mínimo impacto en el hot path del firewall.

**Límite:** ventanas chicas (Ollama) pueden no alcanzar; Gemini suele sí. Medir tokens del corpus.

**No implementar hasta:** opción A mergeada y estable.

---

### Opción C — Caché nativa del provider (Gemini primero)

**Idea:** usar **Context Caching** de Google (y análogos Anthropic/OpenAI después): subir el corpus una vez al provider, referenciar `cache_id` en requests siguientes.

**Pros:** óptimo en costo/latencia en la nube; no reenvía megas en cada request.  
**Contras:** no es uniforme (Ollama no tiene esto); código por adapter; acoplado a Google.

**Diseño sugerido:**

- Extender `GoogleGeminiProvider` (y la interfaz `BaseProvider` solo si hace falta un hook opcional `ensure_corpus_cache`).
- Misma UX que B desde el HUD (`rag_mode: cached` o reutilizar `session` con backend distinto según provider).
- Invalidar cache_id al cambiar corpus fingerprint.
- Ollama / providers sin caché: fallback a A o B.

**No implementar hasta:** B validado en producto, o necesidad clara de optimizar solo Gemini.

---

## Orden sugerido cuando se retome el backlog

1. Etapa 3 UX (o B si el dolor de "no conoce el corpus" sigue siendo critico tras A).
2. Checkpoint etapa 4.
3. Evidencia 5–7, checkpoint 8, lanzamiento 9.
4. B y/o C según necesidad de corpus completo vs costo cloud.
5. Nivel 2/3 solo como visión post-lanzamiento.

---

## Notas de entorno útiles (para cualquier ítem futuro)

- Tooling: backend `uv`, frontend `pnpm`.
- Provider Gemini: key en `.env` (`GOOGLE_API_KEY`, `GEMINI_MODEL_ID`); la selección efectiva es el HUD (`upstream_provider` en `ConfigState`), no solo `UPSTREAM_PROVIDER` del `.env`.
- Handoff a LLM externo: `./run_pack.sh` → `context.txt`.
- Datos privados / logs / `_archive/` / `context.txt` no van a git.
