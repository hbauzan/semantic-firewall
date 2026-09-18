# Bloqueos (2026-09-17 noche, UTC-3)

Murray. El humano duerme. Esto no es un diario: solo lo que **no** se puede mergear o correr sin Héctor.

## PRs abiertos (review mañana)

| Ticket | PR | Notas |
| :--- | :--- | :--- |
| L03 | https://github.com/hbauzan/semantic-firewall/pull/6 | Pirámide lab. Autor `murray-threepwood`. |
| L09 | https://github.com/hbauzan/semantic-firewall/pull/7 | Oracle. Autor `murray-threepwood`. |
| L05 | https://github.com/hbauzan/semantic-firewall/pull/8 | Adapter + compose por digest. Tests mock verdes. |

L01 y L02 ya están en `upstream/main` (#4, #5).

## No tomables hasta merge

| Ticket | Bloqueo | Siguiente |
| :--- | :--- | :--- |
| **L04** AND multi-grano | `BLOQUEADO-por: L03 PR #6` (y usa whitening de L02, que **sí** está en main) | Mergear L03, rama nueva desde `upstream/main`. |
| **L06** INLP + τ | `BLOQUEADO-por: L09 PR #7` (L02 ya en main) | Mergear L09. Golden set 100+100 puede nacer entonces. |
| **L07** egreso hold | L04 + L05 en main | No empezar. |
| **L08** sentence buffer | L07 | No empezar. |
| **L10–L12** campañas | grafo del README de pilares | No empezar. |

## L05 live sidecar

- Docker **client** 29.6.1 está instalado. El **daemon** no contestó (`desktop-linux` sin server). No hubo `docker pull`.
- Compose pinneado: `ghcr.io/huggingface/text-embeddings-inference@sha256:2614a26fcdefcd4e8b2d1265cdfb8d0144b591fe7f7e9db922a38056f7c47ca2` (contenido de `cpu-arm64-latest` al 2026-09-17; el tag `cpu-arm64-1.9` no existe, issue upstream #900).
- Suite default: `cd backend && uv run pytest -q tests/test_tei_adapter.py` (mock). Integration skip sin `RUN_TEI_INTEGRATION=1`.
- Para correr el sidecar mañana: arrancar Docker Desktop, `docker compose -f deploy/tei/docker-compose.yml up -d`, `TEI_ENABLED=true`, después el marker de integration. Comparar `max_abs_delta` contra `backend/tests/embedder_determinism_report.md` (L01: 0 en esta Mac, ST singleton).

## Preguntas de producto (no adiviné)

- ¿Enchufar whitening a prod? No. Lab hasta que un ticket lo liste.
- ¿A/B cosine-only vs filtro nuevo? Diferido. No codeado.
