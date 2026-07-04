# Roadmap

> Lista de tareas activas. Pendientes diferidos: [`roadmap-backlog.md`](./roadmap-backlog.md). Mapa Nivel 1: [`roadmap/`](./roadmap/).

---

## Ahora (cerrar Etapa 5)

- [ ] Correr `calibration_suite.py evaluate` en automotive + medical; revisar mismatches.
- [ ] Correr `sweep` y `excitation-compare` en ambos dominios; anotar número clave de excitación.
- [ ] (Checkpoint 4 deuda) `load_test_suite.py` con backend levantado.
- [ ] Etapa 6: test de determinismo antes de confiar ciegamente en sweep masivo.

Comandos: ver [`backend/calibration/README.md`](./backend/calibration/README.md).

**UI:** botón **Cal** junto a cada pack cargado → `POST /corpus/packs/{filename}/calibrate-positive` (requiere dataset etiquetado para ese filename).
