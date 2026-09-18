# Bloqueos

Actualizado 2026-09-18 (tras merge L01–L03, L05, L09).

## Hecho en main

L01, L02, L03, L05, L09. PRs #4–#8, autor `murray-threepwood`.

## Tomable

| Ticket | Estado |
| :--- | :--- |
| **L04** AND multi-grano | Este PR. Lab. No toca `/chat`. |
| **L06** INLP + τ | Libre en paralelo (L02+L09 en main). |

## No empezar

| Ticket | Hasta |
| :--- | :--- |
| **L07** egreso hold | L04 en main (L05 ya está) |
| **L08** | L07 |
| **L10–L12** | grafo del README de pilares |

## L05 live sidecar (operador)

Docker Desktop es el daemon del sidecar TEI, **no** el semantic-firewall. El firewall sigue bare-metal (`setup-fw.sh`). `TEI_ENABLED=false` por default.

## Producto (no adivinar)

- Whitening / AND / INLP no se enchufan a prod hasta que un ticket lo liste.
- A/B cosine-only vs geometría blanqueada: diferido, no codeado.
