# L01 — Determinismo del embedder actual

> **Estado:** hecho
> **Ola:** 1
> **Spec:** [`specs/pilar-3-tei-determinismo.md`](../specs/pilar-3-tei-determinismo.md)

## Objetivo

Medir, con un script reproducible, si el SentenceTransformer in-process (BGE-M3) emite el mismo vector para el mismo string en N corridas en esta máquina. Dejar fingerprint de entorno. Es el diagnóstico del Documento 2 **antes** del sidecar. No es una feature de producto.

Solapa [`nivel-1/etapa-6-auditoria-evidencia.md`](../../nivel-1/etapa-6-auditoria-evidencia.md) Bloque A. Si Etapa 6 ya tiene el script, reusalo y linkealo; no dupliques harness.

## Depende de

Nada.

## Desbloquea

- L05 (baseline para comparar TEI vs ST)

## Paralelo con

- L02, L03, L09

## Archivos a leer

- [`backend/app/modules/mlx_embedder.py`](../../../backend/app/modules/mlx_embedder.py) — `embed_full`
- [`backend/app/modules/embedder.py`](../../../backend/app/modules/embedder.py)
- [`backend/app/modules/dispatcher.py`](../../../backend/app/modules/dispatcher.py)
- Etapa 6 Bloque A

## Archivos a tocar

- `backend/tests/` — script o test (nombre sugerido: `test_embedder_determinism.py` o script hermánico tipo `calibration_suite.py`)
- Reporte Markdown corto en el mismo directorio de tests o `backend/tests/artifacts/` (gitignored si es binario; el informe de magnitudes sí se commitea si es texto y no tiene corpus privado)

## Fuera de alcance

- Docker, TEI, cambiar el modelo, tocar `firewall.py`
- Prometer bit-exacto cross-host

## Tareas

- [x] Embeber el mismo string N=100 veces vía el backend actual (`embed_full` o dispatcher).
- [x] Hash / igualdad de vectores; si no son bit-idénticos, reportar max |Δ| por coordenada y en norma.
- [x] Repetir decisión PASS/BREACH del firewall para un prompt fijo + corpus fijo (si el test puede cargar pack demo sin red).
- [x] Fingerprint: `embedding_model`, `sentence-transformers`, `torch`, device (`mps|cuda|cpu`), versiones relevantes.
- [x] Documentar el comando exacto: `cd backend && uv run pytest …` o `uv run python tests/…`.

## Tests (TDD)

El test falla (o el script exit≠0) si no puede embeber. La **inestabilidad** no es fallo de CI: se registra. Un assert estricto de igualdad bit a bit solo si el device lo da; si no, documentar tolerancia observada.

```
cd backend && uv run pytest -q tests/test_embedder_determinism.py
cd backend && uv run python tests/embedder_determinism.py --runs 100
cd backend && RUN_EMBEDDER_DETERMINISM=1 uv run pytest -q tests/test_embedder_determinism.py
```

Informe: [`backend/tests/embedder_determinism_report.md`](../../../backend/tests/embedder_determinism_report.md). Harness con stubs siempre corre en la suite; el N=100 live **no** entra en `./run_tests.sh`.

## Definición de hecho

- [x] Comando documentado, N=100 corrido, magnitudes en el informe
- [x] Fingerprint escrito
- [x] L05 puede citar este informe como baseline
- [x] Fila L01 en [`README.md`](../README.md) → `hecho`

## Trampas

- No uses un segundo proceso con distinta semilla de OpenMP y lo llames “el mismo runtime” sin decirlo.
- No subas vectores ni texto de corpus privado.

## Resultado (Darwin arm64 / MPS / torch 2.10.0 / ST 5.3.0 / BGE-M3)

- Vectores densos **bit-idénticos** en N=100 (max_abs_delta=0, unique_hashes=1) para on-corpus y off-topic.
- PASS/BREACH **estable** (flip_count=0). On-corpus: BREACH por excitación contra un chunk de 512 chars (calibración, no jitter). Off-topic: BREACH por coseno.
- Path medido: singleton `embedder.embed_full`. El dispatcher tiene **otra** instancia ST.

## Prompt copiable

```
Usando dev-protocol, tomá roadmap/pilares/tickets/L01-determinismo-embedder-actual.md.
Leé specs/pilar-3-tei-determinismo.md y 00-alcance.md.
Medí determinismo del embedder in-process (100×). No Docker. No cambies el filtro.
TDD / script con uv run. Al cerrar, marcá L01 hecho en el README de pilares.
```
