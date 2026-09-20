# Roadmap

> Lista de tareas activas (Nivel 1). Pendientes diferidos: [`roadmap-backlog.md`](./roadmap-backlog.md).
> Pack paralelo para agentes: [`roadmap/pilares/README.md`](./roadmap/pilares/README.md).
> Mapa: [`roadmap/`](./roadmap/).

---

## Entregado en esta branch — Benchmark suite

Harness offline de validación geométrica (AdvBench + sweep Youden): **hecho**.

- Script: `backend/tests/benchmark_suite.py` — `cd backend && uv run python tests/benchmark_suite.py`
- Reporte: [`benchmark-report.md`](./benchmark-report.md)
- Artefactos (gitignored): `backend/tests/benchmark_metrics.csv`, `benchmark_roc.png`, `decision_boundary.png`

---

## Ahora (cerrar Etapa 5)

- [ ] Correr `calibration_suite.py evaluate` en automotive + medical; revisar mismatches.
- [ ] Correr `sweep` y `excitation-compare` en ambos dominios; anotar número clave de excitación.
- [ ] (Checkpoint 4 deuda) `load_test_suite.py` con backend levantado.
- [ ] Etapa 6: test de determinismo antes de confiar ciegamente en sweep masivo.

Comandos: ver [`backend/calibration/README.md`](./backend/calibration/README.md).

**UI:** botón **Cal** junto a cada pack cargado → `POST /corpus/packs/{filename}/calibrate-positive` (requiere dataset etiquetado para ese filename).
