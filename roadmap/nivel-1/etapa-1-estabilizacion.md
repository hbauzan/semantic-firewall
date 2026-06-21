# Etapa 1 — Estabilización e higiene de repo

> Objetivo: dejar el sistema andando sin crashes sobre un entorno único y limpio (`uv` + `pnpm`), y el repo **seguro para mostrar**. Antes de pulir nada, en este orden: **frenar la fuga de datos privados**, establecer el entorno, y recién después diagnosticar y arreglar.

> **Autoridad de tooling:** todo lo de Python va con `uv run` (nunca `pip`, nunca `source .venv`). Todo lo de frontend con `pnpm`. Lo manda `dev-protocol.md` en la raíz del repo. Léelo si tenés dudas.

---

## Por qué esta etapa va primero, y en este orden

Si esto crashea en un demo, perdés credibilidad en 30 segundos. Pero peor que un crash: si hay datos privados en el repo cuando lo publicás, el daño es de reputación y potencialmente legal (PCI/DSS vos lo sabés mejor que nadie). Y **cada commit nuevo que hagas mientras los datos sigan trackeados arrastra el problema** — por eso la limpieza de historial va **primero**, antes de generar más commits con la migración. **Higiene → entorno → andando.**

---

## Hallazgos concretos ya verificados (no asumas, esto está confirmado)

1. **🔴 DATOS PRIVADOS TRACKEADOS EN GIT.** `backend/data/_last_used.json`, `sniffer_history.json`, `history_benchmark.json` están versionados. Contienen prompts y respuestas interceptados. El `architecture_spec.md` §11.8 **afirma** que todos los `*.json` de `data/` están en `.gitignore` — **es falso, no lo están**. Además existe el commit `decb393 "DATA PRIVADA - ELIMINAR antes de publicar"`: hay datos en el **historial**, no solo en el working tree.

2. **Tooling NO migrado a `uv`/`pnpm` (lo exige `dev-protocol.md`).** El backend tiene `requirements.txt` + `.venv` + un `pyproject.toml` que **solo** configura pytest (sin tabla `[project]`, sin dependencias, sin `uv.lock`). El frontend sigue en npm (`package-lock.json`, no hay `pnpm-lock.yaml`). El protocolo manda `uv` (backend) y `pnpm` (frontend) como única fuente de verdad. **La vieja duda `.venv` vs `sg_env` desaparece**: con `uv` no hay activación manual de venv.

3. **Doc drift en el README.** Menciona `pytest -v perform_tests.py` con "29 tests". Ese archivo **no existe**. La suite real está partida en `backend/tests/test_engine.py`, `test_security.py`, `test_api.py` (+ `conftest.py`). También usa comandos `npm` y venv que ya no aplican.

4. **Doc-sync incompleto.** `dev-protocol.md` §4 nombra `CONTEXT.md` como asset de regeneración del codebase, pero el repo tiene `context.txt` (generado por `run_pack.sh`). Hay que reconciliar nombre y propósito.

5. **Working tree sucio.** Hay cambios sin commitear (chat.py, manifest.json, logs, package-lock). Hay que ordenar antes de seguir.

---

## Tareas

### Bloque A — Higiene de seguridad (🔴 PRIMERO, antes de generar más commits)
La sangría de datos no espera. Esto va antes que la migración para no arrastrar datos en commits nuevos.
- [ ] Agregar `backend/data/*.json` (o `backend/data/`) al `.gitignore`. Decidir si conservás `production.json`/`dev_strict.json` de ejemplo (esos sí, sin datos reales).
- [ ] Sacar del tracking los archivos de datos: `git rm --cached backend/data/_last_used.json backend/data/sniffer_history.json backend/data/history_benchmark.json` (ajustar lista).
- [ ] **Limpiar el historial de git** del commit con datos privados. Usá `git filter-repo` (no `filter-branch`). **Hacelo en una rama/clon de prueba primero.** Si el repo nunca se pusheó a un remoto público, alcanza con reescribir historia local antes del primer push.
- [ ] Verificar que `.env` siga ignorado (✅ ya lo está) y que no haya secrets en ningún `*.json` ni en logs trackeados.
- [ ] Revisar `backend/logs/` — los logs no deberían ir al repo público.

### Bloque B — Migración de tooling a `uv` + `pnpm` (establecer el entorno único)
Sobre la historia ya limpia, dejar un único camino de ejecución antes de diagnosticar.
- [ ] **Backend → `uv`:** declarar dependencias reales en `backend/pyproject.toml` (tabla `[project]` con las deps que hoy están en `requirements.txt`). Generar `uv.lock` con `uv sync`. Verificar que `uv run pytest -v tests/` y `uv run uvicorn app.main:app --reload` funcionen.
- [ ] Mantener `requirements.txt` como **artefacto generado** (`uv pip compile pyproject.toml -o requirements.txt`), no como fuente de verdad.
- [ ] Decidir qué hacer con `.venv` y los scripts `run_*.sh` que la activan: o se actualizan para usar `uv run`, o se deprecan. Una sola verdad.
- [ ] **Frontend → `pnpm`:** `pnpm import` para convertir `package-lock.json` → `pnpm-lock.yaml`, después `pnpm install`. Verificar `pnpm run dev`. Borrar `package-lock.json`.

### Bloque C — Diagnóstico (no arreglar todavía, solo mapear)
- [ ] Correr la suite completa: `cd backend && uv run pytest -v tests/`. Anotar **qué pasa y qué falla**, sin tocar nada.
- [ ] Arrancar backend (`cd backend && uv run uvicorn app.main:app --reload`) y frontend (`cd frontend && pnpm run dev`). Anotar errores de boot, warnings, stack traces.
- [ ] Probar a mano cada flujo: chat, audit, upload PDF, sniffer, proxy `/v1/chat/completions`. Anotar qué crashea o se comporta raro.

### Bloque D — Arreglar los crashes encontrados en Bloque C
- [ ] Arreglar **uno por uno**, un commit por fix, nombre descriptivo. Re-correr tests (`uv run pytest tests/`) después de cada uno.
- [ ] Que la suite pase entera.

### Bloque E — Doc-sync (según dev-protocol.md §4)
- [ ] Actualizar `README.md`: comandos correctos (`uv run pytest tests/`, `uv run uvicorn ...`, `pnpm run dev`), sacar referencias a `perform_tests.py`, venv y npm.
- [ ] Actualizar `architecture_spec.md` §11.8 para que diga la verdad sobre el `.gitignore` (una vez arreglado en Bloque A).
- [ ] Reconciliar `CONTEXT.md` vs `context.txt`: decidir si renombrás/regenerás según el propósito que pide el protocolo.
- [ ] Actualizar `manifest.json` si la migración de tooling cambia el estado declarado.
- [ ] Limpiar el working tree: commitear o descartar lo pendiente con mensajes claros.

---

## Definición de "Etapa 1 terminada"
- [ ] **Cero datos privados** en working tree y en historial de git. `.gitignore` correcto y verificado.
- [ ] Backend corre con `uv`, frontend con `pnpm`. Lockfiles presentes. Sin `pip`/activación manual.
- [ ] Suite de tests pasa entera (`uv run pytest tests/`); sabés qué cubre.
- [ ] Todos los flujos corren sin crashear.
- [ ] README, spec, manifest y CONTEXT reflejan la realidad (tooling, comandos, gitignore).
- [ ] Working tree limpio, historial con commits chicos y nombrados.

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
Leé roadmap/nivel-1/etapa-1-estabilizacion.md, Bloque B, y dev-protocol.md.
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
