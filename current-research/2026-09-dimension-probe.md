# Dimension probe — 2026-09-18 (BGE-M3, este Mac)

Lab, no prod. No toca `evaluate_clause`.
Honor: palabras `DEMO_PAIRS` de [vhectorlab](https://github.com/hbauzan/vhectorlab) (`king/rey` … `cat/gato`) + vocab mechanic/IT/names.
Instrumento: BGE-M3 1024D, MPS, `st-hybrid-mps`. Apple M4, 16 GB, 10 cores.
N = **7619** textos (1077 chunks por familia + tokens). ~4.6 min @ 28 textos/s. El tope de 45 min sobró: el lote se acabó.

Los chunks son **moldes con ranuras**, no páginas de un PDF. Intra-grupo 0.86–0.96: están apretados de más. No repetir esto para “llenar la hora”.

## Coseno de centroides (headline)

| Par | Coseno |
| :--- | ---: |
| cripto vs cripto disfrazada | **0.614** |
| cripto vs LLM (ambos densos) | 0.585 |
| mecanica vs IT | **0.502** |
| IT vs nombres | 0.438 |
| LLM vs poesia | 0.408 |
| cripto vs poesia | 0.407 |
| mecanica vs nombres | **0.387** |

Tokens (n=20, más flojos): mecanica–IT 0.888 centroide / 0.497 par a par. El centroide miente en muestra chica.

Tu expectativa (mecanica≈IT > ambas vs nombres): **sí**.
El disfraz (mismo tema, otra ropa): **se queda cerca**. Otro tema (poesia): **se aleja**.

## Energía

**Seguir:** sobre / holgura relativa / z-score sobre **chunks reales del Prisma** (no más moldes). INLP para el que se disfraza y se queda adentro.

**Soltar:** quemar CPU en más variantes del mismo molde; usar solo tokens `maria/engine/python` como prueba de la tesis; meter IT dentro del galpón Prisma porque “también es técnico” (0.50 no es el mismo dominio).

---

## Probe 2 — Prisma real + rompepepe (misma noche)

903 chunks ES del manual (`om_ng-chevrolet_Prisma_my15-es_AR.pdf.pdf`, export del LanceDB hermano). Más on_corpus / deviation / disguise / piggy generados con fixtures S/Z/fragment + **todas** las mutaciones del Explorer fallback (sin LLM). 8662 textos, ~3.4 min, BGE-M3 MPS.

CLI: `cd backend && uv run python -m calibration.dimension_probe.run`

### Coseno vs centroide Prisma

| Familia | Coseno |
| :--- | ---: |
| on_corpus | **0.875** |
| piggy_full | 0.837 |
| disguise | 0.807 |
| deviation | 0.779 |
| cláusula torta | **0.645** |
| IT | 0.583 |
| nombres | 0.475 |
| poesía | 0.463 |

### Sobre (holgura 5% del rango Prisma)

El % medio de dimensiones “adentro” es ~0.98–1.00 para casi todos: 903 páginas pintan paredes gordas. El candado útil es **fila entera adentro** (las 1024):

| Familia | Filas 100% adentro |
| :--- | ---: |
| prisma_chunk | 1.00 |
| cláusula Prisma (piggy) | 0.125 |
| piggy_full | 0.083 |
| disguise | 0.074 |
| on_corpus | 0.035 |
| deviation | 0.003 |
| torta / nombres / IT / poesía | **0.00** |

Las 6 hipótesis del run salieron **true** (orden, no abismo en el % de dims).

### Energía (después de Prisma)

**Seguir:** coseno de centroides + z-score + sobre **estricto** (todas las columnas). Partir piggy en cláusulas. Recortar chunks raros (índice/radio/garantía) antes de pintar el sobre — si no, la holgura relativa “% de dims” no corta.

**Soltar:** usar “99% de dimensiones adentro” como umbral; más moldes; tratar el sobre crudo de 903 páginas como si ya fuera el control de prod.

---

## Probe 3 — oficio vs lomo (misma noche, después)

Mismas 8662 filas que Probe 2. Se recortan radio / legal / índice / cubiertas **antes** de pintar el sobre. El probe no cambia: se comparan dos candados sobre las mismas mediciones.

Regla de texto, auditable (`calibration/dimension_probe/lomo.py`). No es un umbral de embedding.

| Reason | n | Qué es |
| :--- | ---: | :--- |
| indice | 106 | líderes `. . .` / TOC / ÍNDICE |
| radio | 75 | cap. 7 infoentretenimiento / AM-FM / Bluetooth / EQ |
| legal | 5 | lomo, copyright, factura+Manual de Ventas, cliente 13 |
| cubierta | 3 | Black plate / MY15 sin cuerpo de oficio |
| **oficio** | **714** | el taller que pinta el sobre recortado |
| libro | 903 | crudo |

Vetos: `control remoto de radio` (llave) no es stereo; `estación de servicio` no es radio; PSI + footer no es cubierta; “Consulte … página 7-1” en una puerta se queda.

8662 textos, ~3.3 min @ 44/s, BGE-M3 MPS. Audit: `backend/calibration/dimension_probe/out/lomo_audit.json` (gitignored).

### Coseno no ve el recorte

| Par | Coseno |
| :--- | ---: |
| libro vs oficio (centroides) | **0.997** |
| oficio vs on_corpus | 0.870 |
| oficio vs piggy_full | 0.830 |
| oficio vs cláusula torta | 0.637 |
| oficio vs nombres | 0.465 |

El promedio compensó. 189 páginas menos y el centroide sigue siendo el mismo punto. Reproducible ≠ resolución: acá Coseno da la una y veinticinco.

### Sobre estricto (holgura 5%) — libro 903 vs oficio 714

`mean_frac_dims_inside_5pct` sigue ~0.98–1.0. El corte útil sigue siendo **fila 100% adentro**.

| Familia | Libro | Oficio | Δ filas |
| :--- | ---: | ---: | ---: |
| prisma_lomo (189 recortadas) | 1.000 | **0.439** | 106 afuera |
| prisma_chunk (903) | 1.000 | 0.883 | esas mismas 106 |
| cláusula Prisma (piggy) | 0.125 | 0.078 | −19 |
| piggy_full | 0.083 | 0.055 | −11 |
| disguise | 0.074 | 0.054 | |
| on_corpus | 0.035 | 0.017 | −52 |
| deviation | 0.003 | **0.000** | |
| torta / nombres / IT / poesía | **0.00** | **0.00** | |

z-score medio: sube un pelo (torta 1.062 → 1.069). Misma historia, otra cabeza.

### El span mediano miente igual que el coseno

median 0.13409 → 0.13142. p95 0.17131 → 0.16984. Parece que no pasó nada.

Por eje: **334 / 1024** columnas se achicaron. Mediana del delta = 0. Máximo 0.035 (dim 647). El techo que bajó más lo tenía una página de **índice** (cinturón `. . . 3-8`), no una de aceite. Oficio vs lomo, no “el PDF entero es taller”.

dim1 de la corrida previa (radio +0.039 / torta +0.027) **no** era el eje que más se movía en el min/max global: acá dim1 quedó igual. El ejemplo sigue valiendo como mecanismo; el recorte pegó en **otros** techos (índice/radio).

4 hipótesis de compare: **true** (span oficio < libro; torta 0 estricta; lomo no define el candado; piggy_full cae o igual).

### Energía (después del recorte)

**Seguir:** sobre estricto sobre **oficio**, no sobre el lomo. Guardar spans por eje (el mediano no alcanza). INLP cuando se vea en la hoja: columnas que separan oficio vs torta/radio, no un promedio. Piggy partido ya está.

**Soltar:** leer 0.997 o “median span ≈ igual” como “no cambió nada”; 99% de dims; más moldes; 903 crudos como lock de prod; cablear esto a `evaluate_clause`.

---

## Probe 4 — las 1024, todas (radio vs torta)

Misma corrida BGE-M3. Radio = **75 filas × 1024**. Torta = **400 × 1024**. Cada celda es el valor de esa fila en ese eje. El hash es la fila entera.

Por eje: intervalo de **todas** las filas (min y max del mazo). Sin media. Un top-k es una vista; no es “solo esas se movieron”.

Hoja: `out/radio_torta_all_1024.csv` y `sheet` de 1024 en `out/column_delta.json`. Crudo: `out/rows.npz`.

### ¿Las otras 1019 están quietas?

No. **1024 / 1024** tienen min o max distinto (mínimo |Δext| = 0.0018). Ninguna columna es idéntica.

| |Δext| (max de |Δhi|, |Δlo|) | ejes / 1024 |
| :--- | ---: |
| > 0.001 | **1024** |
| > 0.01 | 977 |
| > 0.02 | 864 |
| > 0.05 | 222 |
| > 0.08 | 19 |
| > 0.10 | 3 |

Mediana |Δext| = 0.035. Máximo = 0.105.

Los intervalos 75 vs 400 **se solapan en 1019 ejes**. Solo **5** son disjuntos:

| dim | radio [lo, hi] | torta [lo, hi] |
| ---: | :--- | :--- |
| 96 | [−0.018, +0.081] | [−0.071, −0.020] |
| 526 | [−0.066, +0.013] | [+0.021, +0.040] |
| 569 | [−0.073, +0.029] | [+0.032, +0.048] |
| 763 | [−0.021, +0.059] | [−0.053, −0.027] |
| 850 | [−0.013, +0.055] | [−0.037, −0.028] |

dim1 (ejemplo de una fila) se mueve y **no** es disjunto: radio [−0.051, +0.042], torta [−0.014, +0.057].

BGE-M3 no vive en [−1, +1] por eje. Radio crudo ≈ [−0.20, +0.26]; torta ≈ [−0.18, +0.27].

### Energía

**Seguir:** la hoja de 1024. Las 5 disjuntas son el corte más duro. INLP, si viene, sobre esas (o las 222 con |Δext|>0.05), no sobre un promedio.

**Soltar:** informar 5 filas y callar las 1019; media de 75 como si fuera el hash; decir que “solo se movieron esas”.

---

## Probe 5 — corte duro (las 1024 votan; las 5 deciden)

Misma `rows.npz`. Sin re-embeber. Cada eje vota `left_only` / `right_only` / `both` / `neither`. El **corte duro** mira solo las disjuntas. El resto no se tira: se cuenta.

CLI: `cd backend && uv run python -m calibration.dimension_probe.hard_cut`

Artefactos: `out/hard_cut.json` (una ficha por fila), `out/hard_cut_radio_torta_rows.csv`, `out/hard_cut_votes.npz` (n×1024, un voto por celda).

### Candado radio vs torta — 5 disjuntas

| Mazo | n | left | right | split | out | fila entera en radio | fila entera en torta |
| :--- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| radio | 75 | **75** | 0 | 0 | 0 | **75** | 0 |
| torta | 400 | 0 | **400** | 0 | 0 | 0 | **400** |
| oficio | 714 | 343 | **0** | 137 | 234 | 0 | 0 |
| índice | 106 | 21 | 0 | 38 | 47 | 0 | 0 |
| piggy_full | 400 | 26 | 1 | 95 | 278 | 0 | 0 |
| nombres | 40 | 8 | 0 | 12 | 20 | 0 | 0 |
| IT | 40 | 0 | 0 | 32 | 8 | 0 | 0 |
| poesía | 40 | 10 | 0 | 26 | 4 | 0 | 0 |
| legal | 5 | 0 | 0 | 2 | 3 | 0 | 0 |
| cubierta | 3 | 1 | 0 | 0 | 2 | 0 | 0 |

75/75 radio y 400/400 torta: el candado no se equivoca en los mazos que lo pintaron. Cero filas de oficio entran en las **1024** de radio. 343 de 714 imitan radio en las 5; **ninguna** imita torta.

Los 75 hashes de radio **no** son el mismo sello. `n_left_only` (ejes solo-radio) va de **361 a 439**. `n_both` 585–663. `n_right_only` = 0 y `n_neither` = 0 (están dentro de su propio sobre). Torta: `n_right_only` 116–146, `n_both` 878–908, `n_left_only` = 0.

piggy_full: una sola fila (i=188) corta `right` en las 5; **no** entra en las 1024 de la torta. La cadena entera no es la cláusula.

### Candado oficio vs torta — 0 disjuntas

Los intervalos de 714 páginas de taller se pisan con la torta en **1024 / 1024** ejes. No hay corte duro. Todas las familias salen `out`. El sobre gordo del oficio no es un hash.

### Energía

**Seguir:** el candado chico (radio↔torta, 5 ejes + las 1024). INLP, si viene, sobre esas 5 (o las 222), no sobre el sobre de 714.

**Soltar:** pintar el hash con 714 páginas y esperar un eje disjunto; promediar los 75; tratar las 5 como si las otras 1019 no votaran; cablear a `evaluate_clause`.
