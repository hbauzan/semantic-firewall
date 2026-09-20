# Roadmap — Three-Headed Semantic Firewall

> Carpeta de navegación. En la raíz de `roadmap/` solo vive este índice. El trabajo tomable está en subcarpetas.

## Dónde está el trabajo activo

| Archivo | Contenido |
| :--- | :--- |
| **[`../roadmap.md`](../roadmap.md)** | **Activo ahora (Nivel 1):** benchmark / Youden. |
| **[`pilares/README.md`](./pilares/README.md)** | **Tomable en paralelo:** 4 pilares del PDF (L01–L12). |
| **[`../roadmap-backlog.md`](../roadmap-backlog.md)** | Diferido: etapas 3–9 Nivel 1, Nivel 3, opciones B/C. |

---

## Cómo está organizado esto

```
roadmap/
├── README.md      ← estás acá (único .md en la raíz)
├── pilares/       ← implementación PDF — tomá un Lxx
├── nivel-1/       ← etapas Nivel 1 — tomá una etapa
├── vision/        ← para qué; no se implementa
└── archivo/       ← estudios Cursor/Gemini; no se implementa
```

---

## Estado

- **Nivel 1 (2026-07-04):** etapas 1–2 hechas; opción A hecha. Activo: [`roadmap.md`](../roadmap.md).
- **Pilares (2026-09-17):** specs + tickets L01–L12 en [`pilares/`](./pilares/README.md). Arranque paralelo: L01, L02, L03, L09.

Visión: [`vision/00-vision-y-niveles.md`](./vision/00-vision-y-niveles.md).  
Nivel 1: [`nivel-1/README.md`](./nivel-1/README.md).  
Pilares: [`pilares/README.md`](./pilares/README.md).  
Estudios (no ejecutar): [`archivo/`](./archivo/README.md).

---

## Principios (resumen)

1. Externalizá el estado en checklists (no en la cabeza).
2. Micro-sesiones; un commit, una cosa.
3. Checkpoints 4 y 8 obligatorios antes de evidencia / lanzamiento.
4. Tooling: `uv` (backend), `pnpm` (frontend). Doc-sync **condicional**.
5. Nivel 3 no se trabaja hasta cerrar Nivel 1. El pack [`pilares/`](./pilares/) sí se puede tomar en paralelo; no pisa el filtro de producción hasta que el ticket lo pida.
