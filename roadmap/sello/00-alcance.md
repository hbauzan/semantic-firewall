# Alcance — Sello

Fecha: 2026-09-19. Herramienta hija. Pack nuevo.

## Qué hay que construir

Un candado geométrico **aparte** del ingress de prod. Paquete `backend/sello/`. Reusa el embedder singleton de este repo. No importa `evaluate_clause`.

1. **Almas chicas.** Tres mazos: `python` (tutorial oficial), `legal` (SPDX MIT / Apache-2.0 / BSD), `receta` (cláusulas de cocina). Fuentes y vetos en [`almas.md`](./almas.md).
2. **Hoja.** Por par de almas: `[lo, hi]` de **todas** las filas en las 1024. Sin media. Sin top-k.
3. **Corte duro.** Label `left` / `right` / `split` / `out` solo en los ejes disjuntos. Las otras 1019 siguen votando; no se tiran.
4. **Ingress.** Partir en cláusulas. Fail closed. Una cláusula que no cabe en un alma permitida, o que cae en un alma vedada de la política, tumba el prompt.
5. **Egreso hold.** El mismo sello sobre el texto **entregado**. No perfil chat (puede soltar media frase).
6. **Proxy hija.** Superficie OpenAI-compatible delante de un LLM libre. El modelo no es el juez.

Artefactos: `backend/sello/out/` (gitignored). Tests: `backend/tests/test_sello_*.py` con `--noconftest` (el conftest de backend ya paga un BGE-M3).

## Claim de este pack

El vector es un hash. Mismo texto + mismo embedder pinneado → misma fila. La decisión es membresía de intervalos y voto por eje, no un coseno a un centroide.

Lab 2026-09 (no se reabre):

- Radio vs torta: 5 disjuntas, 75/75 y 400/400.
- Oficio vs torta: **0** disjuntas. El sobre gordo no se publica.
- 343 oficios imitan radio en las 5; **cero** caben en las 1024. El sello entero es el corte que importa; el duro es el veto rápido.
- Piggy: la cadena entera miente; la cláusula no.

Si un par del demo da 0 disjuntas, el mazo está mezclado: se parte. No se baja un umbral.

## Qué no entra

- Tocar `backend/app/core/firewall.py` / `evaluate_clause`.
- Reabrir o reimplementar L01–L12.
- Cablear whitening / pirámide / AND / INLP a Sello en este pack (INLP es otra etapa, si el disfraz se queda adentro).
- A/B cosine-only vs Sello sobre el path de prod.
- Campañas Z / S / fragment, rompepepe, TEI “por las dudas”.
- Un segundo `SentenceTransformer` en el mismo proceso.
- Harm-classifier, producto para menores, enumerar “contenido dañino”.
- Un alma “todo Python.org” o “todo el recetario”. Eso es oficio gordo.

## Hoy vs destino

| Pieza | Hoy (este repo) | Destino de Sello |
| :--- | :--- | :--- |
| Ingress prod | Noise / Cosine / Excitation | Intacto |
| Lab probe | `calibration/dimension_probe/` (Prisma / radio / torta) | Se **reusa la matemática**, no el CLI ni el PDF |
| Decisión | Centroide / % dims / umbral | Hoja 1024 + corte duro |
| Superficie | `/chat`, `/v1` del firewall padre | Proxy **hija** (S06), proceso o módulo aparte |
| Egreso | `chat` (buffer) o `compliance` | Hold solamente en la hija |

## Destino del código (cuando se tomen los tickets)

```
backend/sello/           ← paquete nuevo
backend/sello/out/       ← gitignored
backend/tests/test_sello_*.py
```

El probe (`calibration/dimension_probe/`) no se convierte en Sello. Sello copia la lección, no el acoplamiento al Prisma.
