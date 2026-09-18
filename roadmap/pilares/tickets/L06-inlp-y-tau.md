# L06 — INLP y umbral τ

> **Estado:** hecho
> **Ola:** 3
> **Spec:** [`specs/pilar-1-geometria.md`](../specs/pilar-1-geometria.md) § subespacio ortogonal.

## Objetivo

Estimar el subespacio prohibido \(P\), calcular \(\|\Pi_P(Y)\|^2\) para un texto, y calibrar \(\tau\) con 100 benignos + 100 evasiones (Oracle de L09 si existe; si no, golden set estático del mismo tamaño). Corte si la energía supera \(\tau\).

## Depende de

- L02 (trabajar en espacio blanqueado)
- L09 (calibración empírica con rompepepe; hasta entonces golden set)

## Desbloquea

- Capa 3 del egreso compliance (L07 puede llamar este módulo cuando ambos existan; L07 no está bloqueado de *empezar* el hold, sí de declarar INLP integrado)

## Paralelo con

- L05, L07 (hold se puede cablear con un stub de proyección)

## Archivos a leer

- Spec Pilar 1
- Módulo de blanqueamiento de L02
- [`rompepepe/`](../../../rompepepe/) cuando L09 esté hecho

## Archivos a tocar

- `backend/app/modules/geometry/inlp.py` (o equivalente)
- Artefacto: base de \(P\) + \(\tau\) serializados
- Tests: `backend/tests/test_inlp.py`
- Dataset lab: 100+100 (JSON de prompts etiquetados `benign|evasion`) en `backend/tests/fixtures/` o generado por L09

## Fuera de alcance

- DLP de identificadores (regex/Luhn es L07)
- Sentence buffering
- Cambiar excitación de prod
- SAE u otras bases

## Tareas

- [x] A partir de embeddings de ejemplos de la clase prohibida (tema, no PAN suelto), estimar \(P\) (INLP / proyección a las direcciones discriminativas). Documentá el procedimiento (autovectores de la clase vs complemento, o INLP iterativo) en el docstring / comentario de módulo, no en un ensayo.
- [x] `projection_energy(y) -> float` = \(\|\Pi_P(Y)\|^2\) sobre \(Y\) ya blanqueado.
- [x] Calibrar \(\tau\): 0 FPR sobre los 100 benignos del set de calibración, máximo recall sobre las 100 evasiones. Guardar el valor y el comando.
- [x] `should_cut(y, tau) -> bool`.
- [x] Tests sintéticos: vector en \(P\) → energía alta; vector ortogonal → energía ~0.

## Tests (TDD)

```
cd backend && uv run pytest -q tests/test_inlp.py
```

## Definición de hecho

- [x] Energía de proyección testada
- [x] \(\tau\) calibrado y serializado con el set 100+100 (estático o L09)
- [x] Fila L06 → `hecho`

Cerrado 2026-09-18. INLP iterativo = diferencia de medias en espacio blanqueado (LDA identidad), luego proyección al complemento. \(\tau\) = máximo de energía benigna (corte estricto `>` → 0 FPR). Golden set estático `benign|evasion` (tema *investment_advice*, no PAN). Oracle L09 no etiqueta tema; no se usó un generador de ataques como etiqueta. CLI: `cd backend && uv run python -m app.modules.geometry.inlp --fixture tests/fixtures/inlp_calibration_100x100.json`. Artefacto live gitignored. `evaluate_clause` intacto.

## Trampas

- \(\tau\) no se “elige a ojo” en el código de prod. Sale del procedimiento empírico del PDF.
- No uses el Explorer de rompepepe como etiqueta de sí mismo.

## Prompt copiable

```
Usando dev-protocol, tomá roadmap/pilares/tickets/L06-inlp-y-tau.md.
Leé specs/pilar-1-geometria.md. Subespacio P, energía ||Π_P(Y)||², calibrar τ con 100+100.
TDD, uv run. Al cerrar, marcá L06 hecho.
```
