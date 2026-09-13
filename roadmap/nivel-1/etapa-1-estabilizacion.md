# Etapa 1 — Estabilización e higiene de repo

> **Estado: HECHA** (cerrada en el ciclo de estabilización; higiene extra de árbol de trabajo en 2026-07-04).

> Objetivo: dejar el sistema andando sin crashes sobre un entorno único y limpio (`uv` + `pnpm`), y el repo **seguro para mostrar**. Antes de pulir nada, en este orden: **frenar la fuga de datos privados**, establecer el entorno, y recién después diagnosticar y arreglar.

> **Autoridad de tooling:** todo lo de Python va con `uv run` (nunca `pip`, nunca `source .venv`). Todo lo de frontend con `pnpm`.

---

## Por qué esta etapa va primero, y en este orden

Si esto crashea en un demo, perdés credibilidad en 30 segundos. Pero peor que un crash: si hay datos privados en el repo cuando lo publicás, el daño es de reputación y potencialmente legal (PCI/DSS vos lo sabés mejor que nadie). Y **cada commit nuevo que hagas mientras los datos sigan trackeados arrastra el problema** — por eso la limpieza de historial va **primero**, antes de generar más commits con la migración. **Higiene → entorno → andando.**

---

## Hallazgos originales (diagnóstico al abrir la etapa — ya resueltos)

> Snapshot histórico. No describe el repo actual; los bloques A–E abajo los cerraron.

1. **Datos privados trackeados en git** (`backend/data/*.json`, historial). → Resuelto: gitignore + `git rm --cached` + limpieza de historial.
2. **Tooling no migrado** (venv/npm). → Resuelto: `uv` + `pnpm`, lockfiles, scripts con `uv run` / `pnpm`.
3. **Doc drift en el README** (`perform_tests.py`, npm/venv). → Resuelto: README y suite en `backend/tests/`.
4. **`CONTEXT.md` vs `context.txt`.** → Resuelto: `CONTEXT.md` = glosario de dominio; `context.txt` = bundle generado por `./run_pack.sh` (gitignored).
5. **Working tree sucio.** → Resuelto al cerrar la etapa (y de nuevo en la higiene extra de 2026-07-04).

---

## Tareas

### Bloque A — Higiene de seguridad (🔴 PRIMERO, antes de generar más commits)
La sangría de datos no espera. Esto va antes que la migración para no arrastrar datos en commits nuevos.
- [x] Agregar `backend/data/*.json` (o `backend/data/`) al `.gitignore`. Decidir si conservás `production.json`/`dev_strict.json` de ejemplo (esos sí, sin datos reales).
- [x] Sacar del tracking los archivos de datos: `git rm --cached backend/data/_last_used.json backend/data/sniffer_history.json backend/data/history_benchmark.json` (ajustar lista).
- [x] **Limpiar el historial de git** del commit con datos privados. Usá `git filter-repo` (no `filter-branch`). **Hacelo en una rama/clon de prueba primero.** Si el repo nunca se pusheó a un remoto público, alcanza con reescribir historia local antes del primer push.
- [x] Verificar que `.env` siga ignorado (✅ ya lo está) y que no haya secrets en ningún `*.json` ni en logs trackeados.
- [x] Revisar `backend/logs/` — los logs no deberían ir al repo público.

### Bloque B — Migración de tooling a `uv` + `pnpm` (establecer el entorno único)
Sobre la historia ya limpia, dejar un único camino de ejecución antes de diagnosticar.
- [x] **Backend → `uv`:** declarar dependencias reales en `backend/pyproject.toml` (tabla `[project]` con las deps que hoy están en `requirements.txt`). Generar `uv.lock` con `uv sync`. Verificar que `uv run pytest -v tests/` y `uv run uvicorn app.main:app --reload` funcionen.
- [x] Mantener `requirements.txt` como **artefacto generado** (`uv pip compile pyproject.toml -o requirements.txt`), no como fuente de verdad.
- [x] Decidir qué hacer con `.venv` y los scripts `run_*.sh` que la activan: o se actualizan para usar `uv run`, o se deprecan. Una sola verdad.
- [x] **Frontend → `pnpm`:** `pnpm import` para convertir `package-lock.json` → `pnpm-lock.yaml`, después `pnpm install`. Verificar `pnpm run dev`. Borrar `package-lock.json`.

### Bloque C — Diagnóstico (no arreglar todavía, solo mapear)
- [x] Correr la suite completa: `cd backend && uv run pytest -v tests/`. Anotar **qué pasa y qué falla**, sin tocar nada.
- [x] Arrancar backend (`cd backend && uv run uvicorn app.main:app --reload`) y frontend (`cd frontend && pnpm run dev`). Anotar errores de boot, warnings, stack traces.
- [x] Probar a mano cada flujo: chat, audit, upload PDF, sniffer, proxy `/v1/chat/completions`. Anotar qué crashea o se comporta raro.

### Bloque D — Arreglar los crashes encontrados en Bloque C
- [x] Arreglar **uno por uno**, un commit por fix, nombre descriptivo. Re-correr tests (`uv run pytest tests/`) después de cada uno.
- [x] Que la suite pase entera.

### Bloque E — Doc-sync
- [x] Actualizar `README.md`: comandos correctos (`uv run pytest tests/`, `uv run uvicorn ...`, `pnpm run dev`), sacar referencias a `perform_tests.py`, venv y npm.
- [x] Actualizar `architecture_spec.md` §11.8 para que diga la verdad sobre el `.gitignore` (una vez arreglado en Bloque A).
- [x] Reconciliar `CONTEXT.md` vs `context.txt`: decidir si renombrás/regenerás según el propósito que pide el protocolo.
- [x] Actualizar `manifest.json` si la migración de tooling cambia el estado declarado.
- [x] Limpiar el working tree: commitear o descartar lo pendiente con mensajes claros.

---

## Definición de "Etapa 1 terminada"
- [x] **Cero datos privados** en working tree y en historial de git. `.gitignore` correcto y verificado.
- [x] Backend corre con `uv`, frontend con `pnpm`. Lockfiles presentes. Sin `pip`/activación manual.
- [x] Suite de tests pasa entera (`uv run pytest tests/`); sabés qué cubre.
- [x] Todos los flujos corren sin crashear.
- [x] README, spec, manifest y CONTEXT reflejan la realidad (tooling, comandos, gitignore).
- [x] Working tree limpio, historial con commits chicos y nombrados.

### Higiene extra (post-cierre, 2026-07-04)
No era bloque de la etapa original; quedó hecha al retomar el trabajo:
- [x] Exports de chats (Gemini/Claude), zip, sellos `.ots`, planes/marketing históricos fuera del árbol de trabajo (`_archive/` local, gitignored).
- [x] `manifest.json` slim (`project` / `version` / `state_schema` / `constraints`); historial de capacidades en `CHANGELOG.md`.
- [x] `./run_pack.sh` genera `context.txt` (briefing + docs centrales + runtime) para handoff a un LLM externo.

---


## Trampas
- **La limpieza de historial es irreversible y va primero.** Cloná o rama de prueba antes. Si ya hay un remoto, coordiná el force-push con cuidado. No la dejes para después: cada commit que agregues mientras tanto la complica.
- **No empieces arreglando crashes.** Limpiá historial (A), establecé el entorno (B), mapeá todo (C), y recién ahí arreglá (D).
- **No mezcles higiene + migración + features.** Esta etapa es repo limpio + entorno único + andando. La belleza es la Etapa 3.

---

## Presupuesto de energía
- Bloque A: 1–2 micro-sesiones. **La más importante** — hacela con cabeza fresca, no al final de una sesión larga. La reescritura de historial asusta; tomate tu tiempo.
- Bloque B: 1–2 micro-sesiones (migración mecánica, pero verificá que todo levante).
- Bloque C: 1 micro-sesión (diagnóstico, anotar).
- Bloque D: tantas micro-sesiones como bugs, una por bug.
- Bloque E: 1 micro-sesión.

---

## Prompts sugeridos

**Higiene de seguridad (Bloque A — primero):**
```
Leé roadmap/nivel-1/etapa-1-estabilizacion.md, Bloque A. Necesito sacar los
datos privados del repo y del historial de git antes de cualquier otra cosa.
Proponeme el plan paso a paso (gitignore, git rm --cached, y limpieza de
historial con git filter-repo), explicame cada comando antes de correrlo, y
trabajá sobre un clon/rama de prueba primero. No toques el historial sin
confirmármelo.
```

**Migración de tooling (Bloque B):**
```
Leé roadmap/nivel-1/etapa-1-estabilizacion.md y Bloque B.
Con la historia ya limpia, migrá el backend a uv: declarar dependencias en
backend/pyproject.toml a partir de requirements.txt, generar uv.lock con
uv sync, y verificar que `uv run pytest -v tests/` y
`uv run uvicorn app.main:app --reload` funcionen. Después migrá el frontend a
pnpm (pnpm import + pnpm install + verificar pnpm run dev). Mostrame el plan
antes de tocar nada.
```

**Diagnóstico (Bloque C):**
```
Leé roadmap/nivel-1/etapa-1-estabilizacion.md, Bloque C. Con el entorno ya en
uv/pnpm, corré la suite (uv run pytest -v tests/) y reportame qué pasa y qué
falla, después arrancá backend y frontend y reportá errores de boot. No
arregles nada todavía — solo diagnóstico y un informe de estado.
```

**Arreglar un crash puntual (Bloque D):**
```
En el flujo [X] del firewall pasa [describir el error/stack trace]. Diagnosticá
la causa raíz, proponé el fix más chico posible, aplicalo con uv run para
ejecutar/testear, y re-corré uv run pytest tests/. Un solo fix, un solo commit
con mensaje descriptivo.
```
