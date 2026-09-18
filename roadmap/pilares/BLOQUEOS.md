# Bloqueos

Actualizado 2026-09-18 (L07 en main, #11).

## Hecho en main

L01–L07, L09. PRs #4–#11.

## Este PR

| Ticket | Estado |
| :--- | :--- |
| **L08** sentence buffer | Este PR. Solo `egress_profile=chat`. Compliance hold no se toca. |

## No empezar

| Ticket | Hasta |
| :--- | :--- |
| **L12** fragmentación | L08 en main |
| **L10 / L11** | tomables en paralelo *después* de este merge (L07+L09 ya están) |

## Producto (no adivinar)

- Ingress Noise / Cosine / Excitation no se reescribe.
- A/B cosine-only vs geometría blanqueada: diferido.
- Chat puede soltar la primera mitad de un PAN partido por `\\n`. CDE usa `compliance`.
