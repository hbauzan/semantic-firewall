# AGENTS — handoff

Si llegás a este repo a laburar el firewall semántico, leé esto **antes** de tomar un ticket o de tocar `evaluate_clause`.

## Pack Sello: vivo

Herramienta hija (hoja 1024 + corte duro). Tickets **S01–S06**.  
Puerta: [`roadmap/sello/README.md`](./roadmap/sello/README.md).  
No toca `evaluate_clause`. No es Lxx.

## Pack L01–L12: cerrado

Implementado y mergeado en `main` (2026-09-18/19, PRs #4–#15).  
**No retomes L01–L12. No reescribas esos módulos “porque el ticket está en el repo”.**

Histórico: [`roadmap/archivo/2026-09-pilares-l01-l12/README.md`](./roadmap/archivo/2026-09-pilares-l01-l12/README.md).  
Puerta: [`roadmap/pilares/README.md`](./roadmap/pilares/README.md).

## Qué es prod y qué es lab

- **Prod ingress:** Noise / Cosine / Excitation. `backend/app/core/firewall.py` / `evaluate_clause`. No lo cambies salvo un ticket **nuevo** que lo liste.
- **Lab:** whitening ZCA, pirámide 4 granos, AND multi-grano, INLP+τ. No se llaman desde `evaluate_clause`.
- **TEI:** sidecar opcional, off por default. No cargues un segundo BGE-M3 “por las dudas”.
- **Egreso:** `egress_profile=chat` (buffer `. ; ? \\n`) o `compliance` (hold). Chat **puede** emitir la primera mitad de un PAN partido por newline; por eso existe compliance.
- **rompepepe:** Oracle puntúa texto **entregado** (`POST /chat`), no `% PASS` de `/audit`. Campañas: `z-exfil`, `s-deviation`, `fragment`.

## Qué no está hecho (otra etapa)

- Cablear whitening / AND / INLP al path de producción.
- A/B cosine-only vs geometría blanqueada (mismo dataset, mismo fingerprint L01).
- Correr campañas Z/S/fragment contra un LLM vivo + TEI pinneado (los tests son mock).
- Reescribir el sentence buffer para “ganar” un reporte.

## Roadmaps

- [`roadmap/sello/`](./roadmap/sello/) — pack **vivo** (herramienta hija). Tomá Sxx.
- [`roadmap/archivo/`](./roadmap/archivo/) — estudios 2026-09 y el pack de pilares **cerrado**. No se ejecuta.
- [`roadmap/nivel-1/`](./roadmap/nivel-1/) — línea de producto/evidencia (etapas 5–9). Distinta de Sello y de pilares. Fechas viejas; no es Lxx.
- [`roadmap/vision/`](./roadmap/vision/) — para qué. No implementar desde ahí.
- [`roadmap.md`](./roadmap.md) — checklist Nivel 1 (Etapa 5). No es backlog de Sello ni de pilares.

## Invariantes

Consultá [`.agents/skills/dev-protocol/lessons-learned.md`](./.agents/skills/dev-protocol/lessons-learned.md) si está en el clone. Commits/PRs: autor Murray o Héctor; nunca footer `Made with Cursor`.
