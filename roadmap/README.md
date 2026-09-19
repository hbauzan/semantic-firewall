# Roadmap

> Índice. Pack **Sello** es el vivo. L01–L12 está cerrado en `main`.

Handoff para agentes: [`../AGENTS.md`](../AGENTS.md).

## Qué está vivo vs qué es histórico

| Archivo | Qué es |
| :--- | :--- |
| **[`../AGENTS.md`](../AGENTS.md)** | Estado real para otra IA. Empezá acá. |
| **[`sello/README.md`](./sello/README.md)** | **Vivo.** Herramienta hija (hoja 1024 + corte duro). Tickets S01–S06. |
| **[`pilares/README.md`](./pilares/README.md)** | **Cerrado.** Puerta; no tickets Lxx. |
| **[`archivo/2026-09-pilares-l01-l12/`](./archivo/2026-09-pilares-l01-l12/README.md)** | Registro del pack L01–L12. No se ejecuta. |
| **[`../roadmap.md`](../roadmap.md)** | Checklist Nivel 1 (Etapa 5, 2026-07). Distinta de Sello y de pilares. Fechas viejas. |
| **[`../roadmap-backlog.md`](../roadmap-backlog.md)** | Diferido: etapas 6–9, Nivel 3, opciones B/C. |
| **[`nivel-1/`](./nivel-1/README.md)** | Producto / evidencia. No es Lxx ni Sxx. |
| **[`vision/`](./vision/README.md)** | Para qué. No se implementa. |
| **[`archivo/`](./archivo/README.md)** | Estudios 2026-09 + pack cerrado. No se implementa. |

```
roadmap/
├── README.md
├── sello/            ← VIVO (S01–S06)
├── pilares/          ← stub CERRADO (no tomes Lxx)
├── nivel-1/          ← producto; no es Sello ni pilares
├── vision/           ← no se implementa
└── archivo/
    ├── 2026-09-*-estudio.md
    └── 2026-09-pilares-l01-l12/   ← tickets/specs históricos
```

## Estado

- **Sello (2026-09-19):** pack vivo. Herramienta hija. Puerta [`sello/README.md`](./sello/README.md). No toca `evaluate_clause`.
- **Pilares L01–L12 (2026-09-18/19):** mergeados, PRs #4–#15. Histórico en [`archivo/2026-09-pilares-l01-l12/`](./archivo/2026-09-pilares-l01-l12/README.md). **No reabrir.**
- **Nivel 1 (última alineación 2026-07-04):** etapas 1–4 hechas; Etapa 5 listada en [`roadmap.md`](../roadmap.md). No es backlog de Sello ni de pilares. No arranques Etapa 5 “porque el markdown lo dice” sin un pedido nuevo.

Prod ingress sigue Noise / Cosine / Excitation. Lab (whitening / pirámide / AND / INLP) no está en `evaluate_clause`. Sello tampoco.
