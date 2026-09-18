# Embedder determinism — L01

Baseline for L05 (TEI vs SentenceTransformer) and Etapa 6 Bloque A.
Jitter is recorded, not treated as a CI failure. Cross-host bit-exactness is not claimed.

## Command

`cd backend && uv run python tests/embedder_determinism.py --runs 100`

Pytest live: `cd backend && RUN_EMBEDDER_DETERMINISM=1 uv run pytest -q tests/test_embedder_determinism.py`

## Runtime fingerprint

- embedding_model: `BAAI/bge-m3`
- sentence-transformers: `5.3.0`
- torch: `2.10.0`
- numpy: `2.5.0`
- python: `3.14.3`
- platform: `Darwin` `arm64`
- device: `mps`
- backend_name: `st-hybrid-mps`
- path_measured: app.modules.embedder.embedder.embed_full (singleton, sequential; dispatcher holds a second ST instance)
- N: 100
- corpus_source: generate_demo_corpora.CORPORA['automotive_maintenance.pdf'] first ingest chunk (512 chars)

## Vector spread

| role | prompt (truncated) | n | dim | unique_hashes | bit_identical | max_abs_delta | max_l2_delta |
| :--- | :--- | ---: | ---: | ---: | :---: | ---: | ---: |
| identity | What is the recommended cold tire pressure for the rear axle on a sedan? | 100 | 1024 | 1 | true | 0 | 0 |
| off_topic | What are the best mutual fund allocations for retirement planning? | 100 | 1024 | 1 | true | 0 | 0 |

## PASS/BREACH spread (frozen automotive chunk, production ConfigState unless noted)

| role | expected | n | stable | flip_count | majority_passed | unique_passed | unique_reasons |
| :--- | :--- | ---: | :---: | ---: | :---: | :--- | :--- |
| on_corpus | pass | 100 | true | 0 | false | [False] | ['excitation'] |
| off_topic | block | 100 | true | 0 | false | [False] | ['cosine'] |

## Notes

- Sequential in-process calls only. A second process with a different OpenMP seed is a different runtime.
- `app.modules.embedder.embedder` and `UnifiedInferenceDispatcher` each construct a SentenceTransformer. L01 measures the singleton `embed_full` path.
- Identity probe reuses the on-corpus query embeddings (same string, N times). Off-topic is a second N loop against the same frozen corpus vector.
- Raw 1024-D vectors are not stored in this report.

## Interpretation

- Dense vectors are **bit-identical** on this fingerprint (N=100, dim=1024, max_abs_delta=0, max_l2_delta=0).
- On-corpus PASS/BREACH is stable (flip_count=0, majority_passed=False, reasons=['excitation']). A stable BREACH here is a calibration/geometry fact, not float jitter.
- Off-topic PASS/BREACH is stable (flip_count=0, majority_passed=False, reasons=['cosine']).
- Cross-hardware bit-exactness (another Mac, NVIDIA, CPU-only) is **not** claimed.
