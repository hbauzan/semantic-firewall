# Roadmap — Three-Headed Semantic Firewall

> Carpeta de navegación del proyecto (mapa interno, no docs públicas).

## Dónde está el trabajo activo

| Archivo | Contenido |
| :--- | :--- |
| **[`../roadmap.md`](../roadmap.md)** | **Activo ahora:** benchmark suite / validación geométrica (Youden). |
| **[`../roadmap-backlog.md`](../roadmap-backlog.md)** | Diferido: etapas 3–9, niveles 2–3, opciones B (sesión corpus) y C (caché provider). Opción A hecha. |

---

## Cómo está organizado esto

```
repo root
├── roadmap.md                    ← ACTIVO (opción A)
├── roadmap-backlog.md            ← backlog (B, C, etapas 3–9, visión)
└── roadmap/
    ├── README.md                 ← estás acá
    ├── 00-vision-y-niveles.md    ← el "para qué"
    ├── nivel-1/                  ← detalle Nivel 1 (1–2 hechas; 3–9 en backlog)
    ├── nivel-2-futuro.md
    └── nivel-3-futuro.md
```

---

## Estado (2026-07-04)

- **Etapas 1 y 2:** hechas (estabilización, tooling `uv`/`pnpm`, logging NDJSON).
- **Opción A (RAG rico):** hecha (`rag_top_k` 12/32, multi-cláusula, telemetría).
- **Siguiente producto:** etapa 3 UX (ver backlog), salvo que B se priorice por dolor de corpus.
- **Tareas del momento:** [`roadmap.md`](../roadmap.md) — harness offline de benchmark (AdvBench + sweep Youden).

Visión y claims: [`00-vision-y-niveles.md`](./00-vision-y-niveles.md).  
Secuencia Nivel 1: [`nivel-1/README.md`](./nivel-1/README.md).

---

## Principios (resumen)

1. Externalizá el estado en checklists (no en la cabeza).
2. Micro-sesiones; un commit, una cosa.
3. Checkpoints 4 y 8 obligatorios antes de evidencia / lanzamiento.
4. Tooling: `uv` (backend), `pnpm` (frontend). Doc-sync **condicional** (ver skill `dev-protocol`).
5. No trabajar Nivel 2/3 hasta cerrar Nivel 1.
