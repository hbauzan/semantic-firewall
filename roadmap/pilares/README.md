# Pilares — pack cerrado

L01–L12 **ya está en `main`** (PRs #4–#15, 2026-09-18/19).

**No hay tickets tomables acá.** No reimplementes el pack. No uses prompts copiables de Lxx.

Registro histórico (specs, tickets, alcance):  
[`../archivo/2026-09-pilares-l01-l12/README.md`](../archivo/2026-09-pilares-l01-l12/README.md)

Qué es verdad ahora, para no marearse:

| Superficie | Estado |
| :--- | :--- |
| Ingress de **producción** | Sigue Noise / Cosine / Excitation en `evaluate_clause`. No se reescribió. |
| Lab (L02–L06) | Whitening, pirámide, AND, INLP+τ. Tablas/scripts aparte. |
| TEI (L05) | Sidecar pinneado, `TEI_ENABLED=false` por default. |
| Egreso (L07–L08) | `egress_profile=chat\|compliance`. Chat = sentence buffer. Compliance = hold. |
| rompepepe (L09–L12) | Oracle + campañas Z / S / fragment vía `POST /chat`. |

Siguiente trabajo (si lo hay) es **otro pack**: cablear lab a prod, A/B cosine, campañas contra LLM vivo. No reabrir L01–L12.

Handoff para agentes: [`../../AGENTS.md`](../../AGENTS.md).
