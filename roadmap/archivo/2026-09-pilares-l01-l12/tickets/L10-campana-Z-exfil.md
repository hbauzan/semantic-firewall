# L10 — Campaña Z: exfiltración

> **Ticket histórico (hecho, pack cerrado).** No lo tomes. No corras el prompt copiable. Código en `main`: PRs #4–#15.

> **Estado:** hecho
> **Ola:** 4
> **Spec:** [`specs/pilar-4-rompepepe.md`](../specs/pilar-4-rompepepe.md) § Campaña 1.

## Objetivo

Campamento de rompepepe que fuerza al target a emitir secretos **plantados** (roleplay, Base64/hex/ROT13, dígitos partidos, inyección indirecta) y mide **0 entregas** vía Oracle. Path: `POST /chat` (texto entregado), no solo `/audit`.

## Depende de

- L07 (sin egreso, esta campaña no prueba el claim de salida; `/audit` no alcanza)
- L09 (Oracle)

## Desbloquea

Nada interno al pack. Informe de leakage.

## Paralelo con

- L11

## Archivos a leer

- Spec Pilar 4
- [`rompepepe/client/explorer_client.py`](../../../../rompepepe/client/explorer_client.py)
- [`rompepepe/client/firewall_client.py`](../../../../rompepepe/client/firewall_client.py) — `chat()` hoy no consume el NDJSON de `/chat`; hay que hacerlo
- [`rompepepe/engines/adaptive_fuzzing.py`](../../../../rompepepe/engines/adaptive_fuzzing.py)
- [`rompepepe/main.py`](../../../../rompepepe/main.py)

## Archivos a tocar

- Dataset: secretos sintéticos plantados (PAN Luhn válido de prueba, API key falsa) + prompts de ataque. **Nada real.**
- `FirewallClient`: consumir stream `/chat` y devolver `delivered_text` + si hubo corte perimetral
- Engine p. ej. `rompepepe/engines/campaign_z.py`
- CLI: `--strategy z-exfil` o equivalente no ambiguo
- Explorer: plantillas del PDF (mantenimiento, auditor forense, ofuscación)
- Tests: `rompepepe/tests/test_campaign_z.py` con HTTP mock (no LLM vivo en default)

## Fuera de alcance

- Campaña S y fragmentación
- Índices extra
- Cambiar el firewall más allá de usar L07

## Tareas

- [x] Corpus de prueba con Z plantado (documentar cómo cargarlo al backend).
- [x] Loop: Explorer → chat → Oracle sobre entregado.
- [x] Técnicas: roleplay, Base64, hex, ROT13, `"4 1 1 1"`, indirección.
- [x] Métrica de éxito FW: leakage rate = 0 en el set fijo; el Explorer puede seguir mutando en modo live.
- [x] Reporte: leakage, no % PASS.

## Tests (TDD)

```
PYTHONPATH=. uv run --project backend pytest -q rompepepe/tests/test_campaign_z.py
```

Desde `rompepepe/`:

```
PYTHONPATH=.. uv run --project ../backend pytest -q tests/test_campaign_z.py
```

## Definición de hecho

- [x] Estrategia runnable documentada
- [x] Oracle puntúa entregado
- [x] Tests mock verdes
- [x] Fila L10 → `hecho`

Cerrado 2026-09-18. `FirewallClient.chat()` consume NDJSON. Banner `[FW_PASS]` no es generación. Stream vacío sin corte ≠ 0 leaks (fail-closed). CLI: `--strategy z-exfil`. Live Explorer: `--live-explorer`. Plantado: `rompepepe/test_dataset/campaign_z.json` (sintético; en live va al system prompt del target, no a LanceDB).

## Trampas

- Secretos reales = incidente. Solo sintéticos.
- Si `chat()` parsea mal el stream, el Oracle verá vacío y mentirá “0 leaks”. Testeá el parser.

## Prompt copiable (NO EJECUTAR)

> Pack cerrado. Este bloque es registro. No lo copies a un agente.


```
Usando dev-protocol, tomá roadmap/pilares/tickets/L10-campana-Z-exfil.md.
Leé specs/pilar-4-rompepepe.md. Campaña Z vía /chat + Oracle. Secretos sintéticos.
TDD, uv run. Al cerrar, marcá L10 hecho.
```
