# Nivel 3 — Firmas registrables / certificación (visión, escala-década)

> Solo ideas. Esto es una expresión de deseo: la dimensión hacia donde apunta tu vector. Coherente, pero NO es un entregable de un dev solo, y la mayoría de sus problemas no son técnicos. No trabajar en esto. Soñarlo, sí.

---

## La idea en una línea

Una **frontera semántica calibrada** se vuelve un artefacto **registrable y reproducible**: una "firma" que una institución carga y obtiene un comportamiento de filtrado certificado. Espacios semánticos seguros para niños, adolescentes, instituciones del Estado; una forma matemática de que un regulador (tipo UE) acote qué pueden hacer los LLMs, transparente respecto a qué proveedor (nube o local) se use por debajo.

---

## Por qué es coherente (no es delirio)

Si una frontera es determinista y portable, entonces es un objeto que se puede:
- **Versionar y firmar** (como una firma de antivirus, pero para regiones del espacio semántico).
- **Auditar** (cualquiera verifica qué bloquea esa firma).
- **Adoptar institucionalmente** (un organismo publica "la firma segura para X" y los deployments la cargan).

La intuición tiene sustento socio-teórico-tecnológico-filosófico. El problema no es la idea — es todo lo demás.

---

## La dependencia técnica que lo habilita (y que arrancás a resolver en el Nivel 1)

Una firma = `corpus + thresholds + embedder_version + runtime_fingerprint`. El eslabón frágil es la **reproducibilidad del embedder** (mismo modelo, misma versión de `sentence-transformers`/`torch`, mismo device → mismos vectores).

**Diseño-objetivo (decidido en el grilling):** la firma contiene **vectores precomputados**, no el corpus crudo. El deployment receptor NO re-embebe el corpus — usa los vectores tal cual + un hash del embedder con el que se generaron, y solo embebe las queries entrantes con el mismo embedder pinneado. Esto reduce el problema a "todos usan el mismo embedder", verificable por hash.

> El experimento de determinismo de la Etapa 6 es la **semilla** de esto. No construís la firma ahí — pero documentás el fingerprint del entorno donde la frontera es estable. Ese es el primer ladrillo, gratis, mientras hacés el Nivel 1.

**Pendiente honesto:** el determinismo **cross-hardware** (otra Mac, NVIDIA, CPU) probablemente no se sostenga bit a bit. Resolver eso (¿tolerancias? ¿cuantización canónica? ¿un servicio de referencia que embebe?) es trabajo de investigación serio, no de producto.

---

## Los problemas que NO son técnicos (los más difíciles)

1. **Gobernanza:** ¿quién certifica? ¿quién firma? Eso es un organismo, no un repo.
2. **Adopción:** una firma solo vale si alguien con autoridad la adopta. Problema de política e instituciones.
3. **Mantenimiento:** una "región segura para niños" tiene que actualizarse contra ataques nuevos para siempre. Es un servicio vivo, no un artefacto estático.

Estos se resuelven conociendo a las personas adecuadas en cada nivel — que aparecerán (o no) a medida que los niveles previos funcionen. O la dirección cambia. Es un vector, no una ruta fija.

---

## El rol de esto en el lanzamiento del Nivel 1

Aparece **solo** como la sección final "Implicaciones" del writeup. Muestra visión sin comprometer fechas. Nunca lidera la comunicación. Regla de oro: **para construir, soñá esto; para publicar, vendé el Nivel 1.**

---

## Cuándo abrir este archivo de nuevo
Cuando el Nivel 1 y el Nivel 2 funcionen, y empieces a cruzarte con gente de gobernanza/regulación/instituciones. No antes. Mientras tanto: es el norte, no la tarea.
