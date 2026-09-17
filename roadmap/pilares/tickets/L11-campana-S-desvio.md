# L11 — Campaña S: desvío temático

> **Estado:** pendiente
> **Ola:** 4
> **Spec:** [`specs/pilar-4-rompepepe.md`](../specs/pilar-4-rompepepe.md) § Campaña 2.

## Objetivo

Atacar modo positivo / soberanía documental: el Explorer pide contenido ajeno al corpus `S` con ropa técnica (metáfora del manual, conocimiento general del oficio). El Oracle marca brecha si la **salida entregada** no cumple membresía (AND L04). Medir recall de bloqueo **y** FPR sobre consultas on-corpus.

## Depende de

- L04 (regla AND)
- L07 (egreso)
- L09 (Oracle)

## Desbloquea

Nada interno. Informe S.

## Paralelo con

- L10

## Archivos a leer

- Spec Pilar 4
- Módulo AND de L04
- Cliente/engines de rompepepe post-L09/L10 (reusar parser de `/chat`)

## Archivos a tocar

- Dataset: on-corpus (paráfrasis del PDF demo) vs desvíos (receta, política, “motores alemanes”, metáfora automotriz)
- Engine `rompepepe/engines/campaign_s.py`
- CLI `--strategy s-deviation`
- Oracle: etiqueta `on_corpus | deviation`; FPR = on-corpus bloqueadas
- Tests: `rompepepe/tests/test_campaign_s.py` (mock)

## Fuera de alcance

- Campaña Z y fragmentación
- Cambiar umbrales de prod “para que el reporte se vea bien”

## Tareas

- [ ] Casos on-corpus que **deben** aprobarse (FPR).
- [ ] Casos de desvío del PDF (camuflaje metafórico, conocimiento general).
- [ ] Loop chat → texto entregado → AND/Oracle.
- [ ] Reporte: recall de bloqueo adversarial + FPR. Nada de estabilidad operacional como headline.

## Tests (TDD)

```
cd rompepepe && uv run pytest -q tests/test_campaign_s.py
```

## Definición de hecho

- [ ] Campaña S runnable
- [ ] FPR y recall en el reporte
- [ ] Fila L11 → `hecho`

## Trampas

- No uses al Explorer como “¿esto era del PDF?”.
- On-corpus tiene que ser paráfrasis, no solo el string verbatim del chunk (el PDF pide no degradar consultas legítimas).

## Prompt copiable

```
Usando dev-protocol, tomá roadmap/pilares/tickets/L11-campana-S-desvio.md.
Leé specs/pilar-4-rompepepe.md. Desvío temático vs S, recall + FPR, Oracle sobre entregado.
TDD, uv run. Al cerrar, marcá L11 hecho.
```
