# L05 — Sidecar TEI

> **Estado:** pendiente
> **Ola:** 2
> **Spec:** [`specs/pilar-3-tei-determinismo.md`](../specs/pilar-3-tei-determinismo.md)

## Objetivo

Correr Text Embeddings Inference como contenedor con **digest SHA256 pinneado**, y un adapter en el seam de embeddings para que FastAPI deje de inferir in-process cuando TEI está habilitado.

## Depende de

- L01 (baseline de ruido del ST; el informe de L05 compara)

## Desbloquea

- L07 (egreso necesita embed rápido y estable por oración)

## Paralelo con

- L04, L06, L09

## Archivos a leer

- [`backend/app/modules/embedder.py`](../../../backend/app/modules/embedder.py)
- [`backend/app/modules/dispatcher.py`](../../../backend/app/modules/dispatcher.py)
- [`backend/app/modules/mlx_embedder.py`](../../../backend/app/modules/mlx_embedder.py) — `EmbeddingOutput`
- [`backend/app/core/settings.py`](../../../backend/app/core/settings.py)
- [`setup-fw.sh`](../../../setup-fw.sh) (línea “Docker not used”)
- L01 informe: [`backend/tests/embedder_determinism_report.md`](../../../backend/tests/embedder_determinism_report.md)

## Archivos a tocar

- `docker-compose.yml` (o `deploy/tei/`) con imagen `ghcr.io/huggingface/text-embeddings-inference@sha256:…` — **nunca** `:latest`
- Adapter p. ej. `backend/app/modules/tei_embedder.py` implementando `embed_full` / `embed_full_batch`
- `settings` + `.env.example` del backend: `TEI_URL`, `TEI_IMAGE_DIGEST`, flag enable
- `dispatcher.py` — elegir backend TEI vs ST
- Docs de arranque que L05 liste: `setup-fw.sh`, `README.md` raíz **solo** si el comando de run cambia (doc-sync condicional)
- Tests: `backend/tests/test_tei_adapter.py` (HTTP mockeado; un test de integración opcional `pytest.mark.integration` si el contenedor está up)

## Fuera de alcance

- Cambiar el modelo a Qwen/Nomic (se queda BGE-M3 o el id que ya usa el proyecto, servido por TEI)
- Borrar ST: queda fallback para tests sin Docker
- Egreso / INLP

## Tareas

- [ ] Compose con digest pinneado y modelo alineado al de `settings.embedding_model`.
- [ ] Adapter HTTP local; timeouts; sin secrets en logs.
- [ ] Flag: TEI on → dispatcher usa adapter; off → ST.
- [ ] Test unitario del adapter con httpx mock: mismo shape que `EmbeddingOutput`.
- [ ] Script o test: 100× el mismo string contra TEI (si integration) y comparar dispersión vs L01.
- [ ] Actualizar la frase de `setup-fw.sh` / README de run cuando Docker pase a ser el path de embed.

## Tests (TDD)

```
cd backend && uv run pytest -q tests/test_tei_adapter.py
```

Integración (no default CI si no hay Docker):

```
cd backend && uv run pytest -q tests/test_tei_adapter.py -m integration
```

## Definición de hecho

- [ ] Contenedor documentado por digest, no por tag flotante
- [ ] Seam único: negocio no llama TEI ad-hoc
- [ ] Tests sin Docker verdes (mock)
- [ ] Fallback ST intacto
- [ ] Fila L05 → `hecho`

## Trampas

- `tei:latest` está prohibido aunque “funcione en tu máquina”.
- No pongas API keys de Hugging Face en el compose commiteado si el pull de modelo las necesita: env.
- Dependencias: `uv add httpx` si no está; nunca pip.

## Prompt copiable

```
Usando dev-protocol, tomá roadmap/pilares/tickets/L05-sidecar-tei.md.
Leé specs/pilar-3-tei-determinismo.md. Sidecar TEI por digest SHA256 + adapter en el dispatcher.
No cambies de modelo. No toques el egreso. TDD, uv run. Al cerrar, marcá L05 hecho.
```
