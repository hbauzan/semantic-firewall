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

## TK-01 — pureza numérica (aprendido en PR #18)

- **Coseno:** el clip `np.clip(dot/(|u||v|), -1.0, 1.0)` en `firewall.py` **se queda**. La división
  flotante puede dar `1.0000000000000002` y eso rompe cualquier trigonometría aguas abajo. Los
  micro-gaps viven en `1.0 - ε` (estrictamente < 1.0), así que el clip no los borra.
- **Presentación ≠ cálculo (Invariante 4):** el mantissa completo (`.17g`) aplica a tensores,
  telemetría y calibración. Los hints al usuario (`[TUNING HINT]`) son texto cosmético: se renderizan
  con el repr más corto (`str(float(v))`), porque `.17g` de un valor floored muestra `0.65299999999999991`.
  El guard repo-wide `test_no_lossy_fixed_decimal_formatting_in_backend_app` prohíbe `:.Nf` en todo
  `backend/app`, incluido el hint; por eso se usa `str(float(...))`, no `.3f`.
- **Sin helpers de paso:** `chat.py` consume el `last_cosine` (float64) que ya devuelve
  `evaluate_clause`. No re-importar helpers de `corpus_calibration` inline en endpoints.
- **Tests dependientes de arquitectura:** no asumir que float32 colapsa exactamente a `1.0`. En ARM64
  con FMA da `> 1.0` (ej. `1.000000238418579`). Asertar el contrato real (gap no representable,
  score no estrictamente < 1.0), no el bit-pattern de un host.

