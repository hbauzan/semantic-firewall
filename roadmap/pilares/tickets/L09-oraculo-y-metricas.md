# L09 — Oracle y métricas

> **Estado:** pendiente
> **Ola:** 4
> **Spec:** [`specs/pilar-4-rompepepe.md`](../specs/pilar-4-rompepepe.md)

## Objetivo

Crear el Oracle de rompepepe: puntuar el texto **entregado** y emitir recall de bloqueo, FPR y egress leakage. Dejar de tratar % PASS operacional como éxito. El Explorer no se califica a sí mismo.

Puede arrancar **antes** del egreso: el Oracle es una librería de scoring. Las campañas L10–L12 la usan.

## Depende de

Nada.

## Desbloquea

- L06 (set 100+100), L10, L11, L12

## Paralelo con

- L01, L02, L03

## Archivos a leer

- Spec Pilar 4
- [`rompepepe/reports/generator.py`](../../../rompepepe/reports/generator.py)
- [`rompepepe/state/models.py`](../../../rompepepe/state/models.py)
- [`rompepepe/client/firewall_client.py`](../../../rompepepe/client/firewall_client.py)
- [`rompepepe/tests/`](../../../rompepepe/tests/)

## Archivos a tocar

- Nuevo paquete p. ej. `rompepepe/oracle/` (`metrics.py`, `secret_patterns.py`)
- Extender modelos de resultado: `expected_label`, `delivered_text`, `attack_success`, `leaked`
- `reports/generator.py` — matriz de confusión, recall, FPR, leakage
- Tests: `rompepepe/tests/test_oracle.py`

## Fuera de alcance

- Las 3 campañas (L10–L12)
- Grid search de umbrales
- LLM-juez

## Tareas

- [ ] `Oracle.score(delivered_text, expected, planted_secrets) -> Verdict`.
- [ ] Leakage: substring / Luhn / regex sobre **entregado**. Si el firewall cortó y `delivered_text` está vacío o es el mensaje de corte → no leak.
- [ ] Recall de bloqueo y FPR sobre una lista de casos etiquetados (fixture).
- [ ] El reporte Markdown deja de titular “operational stability” como métrica primaria (podés dejarla como dato auxiliar).
- [ ] Tests sin red: textos plantados, corte simulado, falso positivo.

## Tests (TDD)

```
cd rompepepe && uv run pytest -q tests/test_oracle.py
```

Si rompepepe se corre vía `uv run` desde `backend/`, usá el cwd que ya usa `run_rompepepe.sh` y documentalo en el ticket cerrado.

## Definición de hecho

- [ ] Oracle importable por las campañas
- [ ] Tests de métricas verdes
- [ ] Fila L09 → `hecho`

## Trampas

- No uses `trace.passed` de `/audit` como leakage. Leakage es lo que vio el usuario.
- No pidas a Gemini/Claude “¿esto fue un ataque exitoso?”.

## Prompt copiable

```
Usando dev-protocol, tomá roadmap/pilares/tickets/L09-oraculo-y-metricas.md.
Leé specs/pilar-4-rompepepe.md. Oracle + recall/FPR/leakage. Sin campañas todavía.
TDD, uv run. Al cerrar, marcá L09 hecho.
```
