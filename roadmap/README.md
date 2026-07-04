# Roadmap — Three-Headed Semantic Firewall

> Carpeta de navegación del proyecto. Esto **no** es documentación pública: es tu mapa interno para ir del estado actual (base estable + logging listo) hasta un lanzamiento público que sirva como artefacto de credibilidad.

---

## Cómo está organizado esto

```
roadmap/
├── README.md                     ← estás acá
├── 00-vision-y-niveles.md        ← el "para qué". Niveles 1/2/3, claim primario, narrativa
├── nivel-1/                      ← EL FOCO. Producto de texto, lanzable. Detallado.
│   ├── README.md                 ← secuencia y definición de "terminado"
│   ├── etapa-1-estabilizacion.md ← HECHA
│   ├── etapa-2-logging.md        ← HECHA
│   ├── etapa-3-ux.md             ← SIGUIENTE
│   ├── etapa-4-checkpoint-testeo.md
│   ├── etapa-5-automatizacion-calibracion.md
│   ├── etapa-6-auditoria-evidencia.md
│   ├── etapa-7-benchmark-comparativo.md
│   ├── etapa-8-checkpoint.md
│   └── etapa-9-plan-lanzamiento.md
├── nivel-2-futuro.md             ← bidireccional (filtrar salida del LLM). Solo ideas.
└── nivel-3-futuro.md             ← firmas registrables / certificación. Solo ideas.
```

---

## Principios de trabajo (adaptados a tu realidad)

Sos un tipo solo, viudo, con un hijo adolescente con TEA, en burnout, que construye con IA. Este roadmap está diseñado **alrededor de eso**, no contra eso.

1. **Externalizá el estado, no lo sostengas en la cabeza.** Cada etapa tiene un checklist. Tildás lo hecho. Si te vas tres semanas, volvés y el archivo te dice exactamente dónde estabas. No dependés de tu memoria de trabajo (que el TDAH te castiga).

2. **Micro-sesiones resumibles.** Cada etapa está partida en bloques de ~30-90 min que cierran solos. Nunca dependés de "terminar todo de una". Un commit chico al final de cada bloque = progreso guardado.

3. **El artefacto trabaja por vos.** El objetivo del lanzamiento no es que vos hagas networking (no tenés la red ni la energía). Es producir un **writeup + repo** tan claros que se defiendan solos mientras dormís. La gente seria te escribe por DM, no comenta en el thread.

4. **Un commit, una cosa.** Nada de commits gigantes "varios ajustes". Cada cambio chico y nombrado. Esto te protege a vos (podés revertir) y le da seriedad al repo público (historial limpio).

5. **No optimices lo que todavía no medís.** Estás en R&D. Primero que ande y midas, después mejorás. La tentación de pulir matemática antes de tener un baseline es la trampa principal.

6. **Checkpoints obligatorios.** Las etapas 4 y 8 son **parates**. No son opcionales. Son donde decidís si seguís derecho o corregís rumbo. Saltearlas es como deployar a producción sin mirar los logs.

7. **El tooling lo manda `dev-protocol.md`.** Backend con `uv run` (nunca `pip` ni `source .venv`), frontend con `pnpm`. Doc-sync es **condicional**: `manifest.json` (versión + `state_schema` + `constraints`), `CHANGELOG.md` (releases / capacidades notables), `architecture_spec.md`, `README.md`, `CONTEXT.md` — solo cuando el cambio los afecta. Para handoff a un LLM externo: `./run_pack.sh` → `context.txt` (gitignored).

---

## El estado real HOY (2026-07-04)

- **Etapas 1 y 2 del Nivel 1: hechas.** Repo higienizado, tooling `uv`/`pnpm`, tests partidos y en verde, flujos operativos, trazas exportables (NDJSON).
- **Siguiente foco: Etapa 3 (UX / flow).** Después el checkpoint de la Etapa 4, y recién ahí investigación (5–7) y lanzamiento (8–9).
- **Tooling:** backend `uv` (`backend/pyproject.toml` + `uv.lock`); frontend `pnpm` (`packageManager` pineado). Scripts: `./run_server.sh`, `./run_ui.sh`, `./run_tests.sh`.
- **Tests:** `backend/tests/test_engine.py`, `test_security.py`, `test_api.py` (+ `conftest.py`). Suites de carga: `load_test_suite.py`, `db_stress_suite.py` (correrlas en Etapa 4).
- **Higiene:** `backend/data/*.json` y `backend/logs/` gitignored; historial sin datos privados de runtime. Exports/chats históricos y marketing viven en `_archive/` local (gitignored), no en el árbol de trabajo.
- **Docs vivos:** `CONTEXT.md` (dominio), `manifest.json` (slim: versión + schema), `CHANGELOG.md` (capacidades), `architecture_spec.md` (LLD), `README.md` (cómo correr).
- **Pack para agentes:** `./run_pack.sh` genera `context.txt` (briefing + docs centrales + código runtime). `--all` incluye `roadmap/`.

---

## Por dónde seguir

1. Si es la primera vez en el roadmap: leé `00-vision-y-niveles.md` una vez. Es el norte.
2. Andá a `nivel-1/README.md` (secuencia y checklist de “Nivel 1 terminado”).
3. **Trabajá en** `nivel-1/etapa-3-ux.md`.
4. No mires el Nivel 2 ni el 3 hasta terminar el Nivel 1. En serio. Son canto de sirena.

---

## Cómo usar los "prompts sugeridos"

Cada etapa termina con prompts listos para pegar en una sesión nueva de Claude Code (o el asistente que uses). Están escritos para ser **autocontenidos**: referencian el archivo de la etapa para que el asistente lea el contexto antes de actuar. Usalos como punto de arranque, no como guion rígido.
