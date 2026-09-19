# Plantilla de ticket

**Histórico.** No creés tickets Lxx acá. El pack L01–L12 está cerrado. Un pack nuevo usa otra carpeta.

```markdown
# Lxx — título

> **Estado:** pendiente
> **Ola:** 1 | 2 | 3 | 4
> **Spec:** specs/pilar-….md

## Objetivo
Un párrafo. Qué queda hecho cuando el ticket cierra.

## Depende de
- Lxx (o "nada")

## Desbloquea
- Lxx

## Paralelo con
- Lxx

## Archivos a leer
- path (por qué)

## Archivos a tocar
- path (qué cambia)
- tests: path

## Fuera de alcance
Lista corta. Si no está en el PDF de este pilar, no.

## Tareas
- [ ] …

## Tests (TDD)
Rojo primero. Comando:

```
cd backend && uv run pytest -q tests/<archivo>
```

(rompepepe: `cd rompepepe && uv run pytest -q tests/<archivo>`.)

## Definición de hecho
- [ ] …
- [ ] Tabla en `roadmap/pilares/README.md` → `hecho`

## Trampas
- …

## Prompt copiable

```
NO EJECUTAR. Pack cerrado. No copies este prompt.
Leé la spec citada y 00-alcance.md. No implementes nada fuera de ese ticket.
TDD. uv run. Al cerrar, marcá el ticket y la fila del README como hecho.
```
```
