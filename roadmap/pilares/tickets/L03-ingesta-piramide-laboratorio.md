# L03 — Ingesta pirámide (laboratorio)

> **Estado:** hecho
> **Ola:** 1
> **Spec:** [`specs/pilar-2-ingesta-fractal.md`](../specs/pilar-2-ingesta-fractal.md)

## Objetivo

Picar un PDF demo en 4 granos (oración, párrafo, sección, documento) con linaje, y guardarlo en una **tabla LanceDB distinta** de `knowledge`. El ingestor de producción (`chunk_text` 512/50) no se reemplaza en este ticket.

## Depende de

Nada.

## Desbloquea

- L04 (AND necesita `parent_id` / granos)
- L11 (desvío S se juega contra grano oración + padre)

## Paralelo con

- L01, L02, L09

## Archivos a leer

- [`backend/app/modules/ingestor.py`](../../../backend/app/modules/ingestor.py) — `_extract_pdf_text`, `chunk_text`, `process_pdf_async`
- [`backend/app/modules/storage.py`](../../../backend/app/modules/storage.py) — `rabitq_schema`, `KnowledgeNode`
- [`backend/app/api/endpoints/corpus.py`](../../../backend/app/api/endpoints/corpus.py)
- PDFs: `backend/demo_corpus/automotive_maintenance.pdf`

## Archivos a tocar

- Nuevo módulo p. ej. `backend/app/modules/fractal_ingest.py` (lab). Puede vivir bajo `backend/tests/lab/` si se quiere aislamiento máximo; tiene que ser importable por L04.
- Schema/tabla lab p. ej. `knowledge_pyramid` (nombre fijo, documentado).
- Tests: `backend/tests/test_fractal_ingest.py`

## Fuera de alcance

- Migrar `knowledge`
- Cambiar `POST /corpus/upload-pdf` de prod
- AND de decisión (L04)
- TEI (embeber con el embedder actual está bien)

## Tareas

- [x] Extraer texto **por página** (hoy se concatena y se pierde `page`).
- [x] Segmentar: oraciones, párrafos, secciones (headings / saltos de página como proxy de sección si el PDF no trae outline), centroide documento (media de vectores o embed del texto agregado — documentá cuál y por qué).
- [x] Asignar `node_id`, `pack_id`, `grain`, `parent_id`, `section_id`, `page`, `char_span`, `text`, `vector`, `sparse`.
- [x] Insertar en tabla lab. Tests: cada `sentence` tiene `parent_id` que existe como `paragraph`; `char_span` apunta a substring real; `grain` ∈ set cerrado.
- [x] Comando: ingerir el PDF automotive de demo a la tabla lab.

## Tests (TDD)

Rojo: no hay pirámide. Verde: linaje íntegro sobre fixture de texto corto (no hace falta el PDF entero en el unit test) + un test de integración opcional con el PDF demo marcado si es lento.

```
cd backend && uv run pytest -q tests/test_fractal_ingest.py
```

## Definición de hecho

- [x] 4 granos persistidos con schema del spec
- [x] Tabla `knowledge` intacta
- [x] L04 puede leer nodos lab (`load_pyramid`)
- [x] Fila L03 → `hecho`

Cerrado 2026-09-17. Módulo `app.modules.fractal_ingest`. Tabla fija `knowledge_pyramid`. Grano `document` = media de vectores `sentence` (mismo espacio que la inspección micro; no `embed` del PDF concatenado). Secciones = un nodo por página (proxy; los demo PDF no traen outline). Si el PDF no está en disco, el CLI usa `generate_demo_corpora.py`. L04: `load_pyramid(db_path, pack_id=...)`.

## Trampas

- No reuses `chunk_text` de 512 chars y le pongas `grain="sentence"`.
- `char_span` contra el texto fuente, no contra el chunk ya cortado.
- No explotes el índice: un PDF demo de pocas páginas. No indexar un manual de 400 páginas en este ticket.

## Prompt copiable

```
Usando dev-protocol, tomá roadmap/pilares/tickets/L03-ingesta-piramide-laboratorio.md.
Leé specs/pilar-2-ingesta-fractal.md y 00-alcance.md.
Pirámide 4 granos en tabla LanceDB aparte. No migres knowledge ni el upload de prod.
TDD, uv run. Al cerrar, marcá L03 hecho.
```
