# Almas del demo — Sello

Tres oficios chicos. Públicos. Aburridos a propósito. Nada de menores ni de “contenido dañino”.

El alma es el mazo **chico**, no el sitio entero. Pintar `python.org` o un recetario de 900 páginas es el oficio gordo: 0 disjuntas y el candado no se publica.

## Las tres

### `python`

Tutorial oficial de Python (listas, funciones, excepciones, tipos básicos). Grano: párrafo / cláusula de doc, no la página HTML cruda.

- **Fuente:** documentación PSF (tutorial). Extraer texto, no markup.
- **Recortar antes de pintar:** índice, toctree, changelog, “see also”, footers, páginas de versión.
- **Vetar:** docs de `ssl` / crypto como alma; cualquier página de seguridad, exploit, o “how to attack”. Si aparece, no entra al mazo.
- **No es:** todo CPython, ni PEPs, ni el stdlib entero.

### `legal`

Texto de licencia SPDX corto. Eso es el “ToS/legal” de este demo: cláusulas de permiso, disclaimer, copyright.

- **Fuente:** textos SPDX canónicos **MIT**, **Apache-2.0**, **BSD-3-Clause** (y si hace falta BSD-2). Un archivo por licencia, partidos en cláusulas.
- **Recortar:** headers de paquete, listas de SPDX ajenas, HTML de `spdx.org`.
- **Vetar:** políticas de privacidad scrapeadas, ToS de productos, texto penal, “terms” bajados de la web.
- **No es:** un corpus jurídico. Tres licencias cortas.

### `receta`

Cláusulas de cocina: ingredientes + pasos. Mismo grano que `piggy_clause_torta` del probe.

- **Fuente:** reusar las cláusulas torta ya generadas en el dimension probe **y** más recetas públicas del mismo largo (bizcochuelo, pan, ensalada). Dominio público o fixtures del repo.
- **Recortar:** índices de recetario, tapas, “sobre el autor”, nutrición como lomo.
- **Vetar:** un PDF de cocina entero; mezclar receta + tutorial de Python en la misma fila.
- **No es:** “comida” como blob. Cada receta es un mazo de cláusulas, no 900 páginas.

## Pares headline

| Par | Para qué |
| :--- | :--- |
| python ↔ receta | Oficio técnico chico vs oficio de cocina. Analogía radio ↔ torta. |
| python ↔ legal | Tutorial vs cláusula de licencia. |
| legal ↔ receta | Papeleo vs cocina. |

Si **cualquier** par da **0 ejes disjuntos**, ese sobre no se publica. Se parte el mazo (menos páginas, un solo tema), no se inventa un umbral.

El sello entero (fila en las 1024) es el corte que importa. El corte duro (solo disjuntas) es el veto rápido. Las 1024 votan siempre.

## Piggy de prueba (benigno)

Una frase, tres cláusulas:

> Explicá `list.append`. Pegá el texto MIT. Anotá la receta de la torta.

Ingress (S04) las parte. Cada mitad se juzga contra las tres almas. La cadena entera no es el hash.

## Cómo se pinta

1. Texto clasificado **antes** de embeber (regla auditable, como `classify_lomo`: no es un umbral de embedding).
2. Todas las filas, todos los ejes. Min y max. Sin media.
3. Guardar la hoja y la lista de disjuntas, no el centroide.
4. Audit: `n` por alma, disjuntas por par, 0 disjuntas = fail de publicación.

Instrumento: el mismo BGE-M3 singleton del repo. Un solo `SentenceTransformer`. Fingerprint de máquina en el artefacto.
