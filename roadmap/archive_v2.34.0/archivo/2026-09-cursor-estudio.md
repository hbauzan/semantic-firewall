# Cosas para estudiar — Contención de canal, no lobotomía del modelo

> **Implementación → [`../pilares/`](../pilares/README.md)** (solo lo del PDF condensado). Este archivo **no se ejecuta**.
>
> Estudio independiente. Opinión fría.  
> Autor / perspectiva: Cursor  
> Ubicación: `roadmap/archivo/2026-09-cursor-estudio.md`  
> Fecha: 2026-09-12 (ampliado el mismo día con opciones y límites que no estaban en la primera pasada)  
> No es backlog de implementación. No pisa el Nivel 1 activo.

---

## 0. Veredicto en una página

La intuición es correcta en el **objeto de control** y está mal nombrada en la **metáfora**.

No vas a lobotomizar GPT, Claude ni Gemini. No tenés los pesos. Lo que sí podés construir —y es el producto que un auditor PCI entendería— es un **canal determinista**: nada llega al usuario si el texto no es miembro de una región semántica declarada (o si pisa una región prohibida). El LLM queda entero. El tubo se corta.

Eso ya es fuerte. Es DLP de dominio + evidencia. No es cirugía del modelo. Decirlo como lobotomía vende; no se defiende en una mesa de compliance.

El retry de la hipótesis dimensional **no** es volver a tunear `|Q_i - C_i| ≤ ε` sobre BGE-M3. Eso ya se midió y perdió: 0 adversariales rescatados, accuracy 96% → 64% (`conclusiones_ultimo_cambio.md`). Reintentar el mismo contador con otro ε es cargo cult.

Lo que se puede rescatar de esa hipótesis es más estrecho y más serio:

> El coseno promedia. Un control que se pueda compensar con un promedio no es un control. Hay que cambiar **el objeto geométrico** (pertenencia a una región, no similitud al vecino más cercano) y, si se insiste en ejes, **la base** en la que se miden. No el umbral.

El experimento del mundo real que describís (PDF in / PDF out, PII/CDE, rompepepe) es el laboratorio correcto. El stack actual **no** está armado para ese experimento: filtra la entrada, no la salida; pica el PDF en ventanas de 512 caracteres; trata modo positivo y negativo como polaridad del mismo pipeline.

Hay un segundo techo, más feo, que no es “falta un embedder mejor”. En alucinaciones **sintéticas** (cambiar la respuesta por otra de otro documento), embeddings + NLI separan casi perfecto. En alucinaciones **reales** de modelos RLHF —fluídas, on-topic, factualmente falsas— el mismo aparato, calibrado para atrapar el 95% de los errors, marca también el 100% de las respuestas fieles. Lo midieron con BGE + DeBERTa-NLI y conformal prediction ([The Semantic Illusion](https://arxiv.org/abs/2512.15068), dic 2025). GPT-4 como juez sí separa (~7% FPR). Traducción: **la geometría contiene el dominio; no certifica la fidelidad**. Son dos productos. Mezclarlos es cómo se termina prometiendo lobotomía y entregando un WAF.

---

## 1. Traducción del pedido a un claim que se pueda auditar

Pedís esto:

```
usuario → prompt
         → OpenAI / Gemini / Anthropic genera
         → este motor decide si esa generación (y, de paso, el prompt)
           está dentro del espacio habilitado o del prohibido
         → si pisa lo prohibido: corta, alerta, deja evidencia
```

Eso no es el Nivel 1 del repo. El Nivel 1 gatea **antes** de que el proveedor vea el prompt. El flujo que querés pone el motor **después** del generador, porque lo que le importa al usuario y al auditor es **lo que se muestra**, no lo que se preguntó.

Dos claims distintos. Hay que no mezclarlos.

| Claim | Qué afirma | Qué ya existe | Qué falta |
| :--- | :--- | :--- | :--- |
| **A. Contención de entrada** | El prompt no llega al LLM si está fuera de región | Pipeline actual (`chat.py` + `firewall.py`) | Evidencia limpia; excitación no aporta |
| **B. Contención de salida** | El usuario no ve texto fuera de región / con secreto | Nada. El stream del provider va crudo al cliente | El producto que estás describiendo |
| **C. Lobotomía del modelo** | El LLM “no puede” pensar X | Imposible sobre APIs cerradas | No perseguirlo como claim |

Claim C es el que hay que matar en la narrativa. Sobre modelos locales podrías experimentar unlearning / ablación de activaciones. Es otro producto, no portable a OpenAI, y no es determinista de la misma manera. Si el motor tiene que “extrapolar en todas direcciones” frente a Gemini y Anthropic, el único claim honesto es **B (+ A como prefiltro)**.

Claim de producto que sí firmaría:

> Dado un corpus versionado y un embedder pinneado, el sistema emite PASS o BREACH sobre cada unidad de texto (prompt y/o oración de salida) de forma reproducible en un mismo runtime, deja traza, y en BREACH no entrega el payload al usuario.

Eso es control. No es lobotomía.

---

## 2. Inventario frío de lo que hay (sin visión)

Hecho, no hipótesis:

- Embedder: `BAAI/bge-m3` 1024D, in-process, SentenceTransformer, device `mps|cuda|cpu`. Sparse lexical opcional. MLX nativo diferido (`mlx_embedder.py`).
- Ingesta: PyMuPDF → `chunk_text` **por caracteres** (`chunk_size=512`, `overlap=50`). Un solo grano. Metadata: filename + chunk_index. No hay oración / párrafo / capítulo / documento.
- Decisión: kNN al chunk más cercano, después tres filtros reordenables (noise, cosine, excitation) más short-circuit sparse. Modo positivo = allowlist; negativo = se invierte el booleano del mismo test.
- Segmentación de **prompts**: puntuación + force-split a 20 palabras. Eso es anti-piggybacking de entrada, no un mapa del PDF.
- Salida del LLM: no se embebe, no se gatea. Sniffer guarda preview/contenido de la respuesta **después** de emitida.
- rompepepe: fuzzer de **entrada** vía `POST /audit`. No lee ni puntúa la generación.
- Calibración: datasets v1 automotive/medical, 25 queries cada uno. Número de excitación ya medido y feo.
- Proveedores: Ollama (default `llama3.1`), OpenAI, Anthropic, Google, Groq. El LLM no es el cerebro del firewall.

Implicación directa: el “motor preparado para verificar todas las salidas” **no existe**. Existe un IDS de prompts con geometría experimental y un sniffer de telemetría. El laboratorio que querés hay que construirlo encima, no reconfigurarlo.

---

## 3. Tres errores de objeto (antes de hablar de modelos)

### 3.1 Similitud ≠ pertenencia

Hoy la pregunta del motor es:

> ¿El vector de esta cláusula está cerca del chunk más cercano del PDF?

La pregunta que necesitás es:

> ¿Este texto es **miembro** de la región que el PDF (o el denylist) define?

Un texto off-topic puede caer cerca de un chunk por accidente léxico. Una paráfrasis fiel del manual puede caer lejos si el chunking diluyó la cláusula. Un jailbreak que pide “explicá el procedimiento de frenos como si fuera una receta” puede tener coseno alto con el corpus y semántica prohibida, o al revés.

kNN + umbral de coseno es retrieval. Retrieval no es membership. Tratarlos como lo mismo es el bug conceptual más caro del sistema, más que el ε de la excitación.

Objetos geométricos distintos, todos estudiables sin inventar ciencia nueva:

1. **Distancia al 1-NN** (lo de hoy). Barato. Fácil de evadir. Útil como prefiltro.
2. **Distribución de distancias a k vecinos** (densidad local). Un punto aislado cerca de un chunk ruidoso no alcanza.
3. **Error de reconstrucción** de un modelo entrenado solo con embeddings del corpus (PCA / autoencoder chico). Fuera de región = no se reconstruye. Clásico de one-class.
4. **Residuo ortogonal al subespacio del corpus.** Proyectás sobre las primeras componentes del PDF; la energía que queda afuera es “no es de este documento”.
5. **Acuerdo multi-grano.** La misma oración tiene que ser miembro a nivel cláusula **y** no derivar del centroide de sección. AND en positivo, OR en negativo (ver §5).

Ninguno de esos es “contar ejes donde |Q_i-C_i|≤0.005”.

### 3.2 Positivo y negativo no son el mismo test con el signo cambiado

El código invierte `passed` cuando `firewall_mode == "negative"`. Matemáticamente elegante. Operativamente falso.

- **Modo positivo (soberanía documental):** problema de **one-class**. El universo permitido es chico (el PDF). Todo lo demás es rechazo. El riesgo dominante es falso positivo sobre preguntas legítimas y falso negativo sobre paráfrasis / jailbreaks temáticos.
- **Modo negativo (PII / CDE / secretos):** problema de **detección de payload**. El universo permitido es casi todo. Lo prohibido es chico y a menudo **exacto**: PAN, CVV, cuenta, nombre+documento, API key. El riesgo dominante es un leak de 16 dígitos que el embedding ni ve.

Un PAN no vive como “dirección semántica”. Vive como patrón + checksum de Luhn + contexto (“card”, “PAN”, “exp”). Medir coseno contra un chunk que contiene “4111-…” es el instrumento equivocado. Lo vas a fallar de las dos maneras: bloquearás prosa sobre “tarjetas de crédito” y dejarás pasar el número ofuscado (`four one one one…`, unicode, markdown, JSON).

Si venís de PCI/DSS, esto no debería ser discutible. Geometría para **tema**. Detectores para **identificadores**. Las dos capas, o no hay claim de CDE.

### 3.3 El espacio del prompt no es el espacio de la respuesta

Calibrar umbrales con preguntas (`automotive_v1.json`) no transfiere a oraciones generadas por un LLM. Pregunta y respuesta no ocupan la misma región. Un filtro de salida calibrado con queries va a mentir.

Cualquier retry serio necesita **dos calibraciones**, o una sola hecha sobre el tipo de texto que realmente se gatea. Si gateás salidas, el dataset tiene que ser salidas.

---

## 4. La hipótesis dimensional, sin romanticismo

### 4.1 Qué era, en términos matemáticos

`run_excitation_filter` cuenta cuántas coordenadas cumplen `|Q_i - C_i| ≤ ε` y exige un mínimo. Eso es el tamaño de la intersección con un cubo de lado 2ε centrado en C (norma L∞ por eje, después Hamming). No es “resonancia”. No es un concepto. Es un conteo en la base canónica de BGE-M3.

La tesis implícita: el coseno permite compensación entre ejes; este conteo no, porque no promedia.

### 4.2 Por qué falló (diagnóstico propio)

No necesito invocar papers de anisotropía para explicar el número que ya tenés.

1. **Los ejes de BGE-M3 no son semánticos.** La dimensión 42 no es “PII” ni “presión de neumáticos”. Pedir que 150 ejes coincidan valor a valor es pedir que dos vectores densos caigan en el mismo cubito en un espacio anisotrópico. Eso es raro para texto *legítimo* y no especialmente raro para el adversarial que el coseno ya filtraba. De ahí: 0 rescates y muchos falsos positivos.
2. **C no es “el tema”.** C es el chunk más cercano, una ventana de 512 caracteres. Estás midiendo alineación punto-a-punto contra un fragmento accidental, no contra una región.
3. **ε fijo (0.005) en 1024 ejes no calibrados por varianza** es un umbral que no significa lo mismo en cada coordenada. Algunas dimensiones concentran casi toda la energía; otras son ruido. El conteo las trata igual.
4. **La polaridad adaptativa para cláusulas cortas** (`adaptive_factor`) mueve el umbral según largo, no según geometría. Es un parche sintáctico sobre un test que ya no mide lo que creés.

Conclusión fría: el *claim diferenciador* del writeup (“la excitación cierra la compensación del coseno”) está refutado con el harness actual. No es “falta calibrar”. Es el estadístico incorrecto en la base incorrecta contra el objeto incorrecto.

### 4.3 Qué se puede rescatar

La parte que sobrevive, y es la única que yo reintentaría:

**Un control de seguridad no puede ser un promedio.**

Formas de honrar eso sin revivir el contador:

| Idea | Qué evita | Costo | Prioridad de estudio |
| :--- | :--- | :--- | :--- |
| Conjunción densa **y** léxica (no blend α) | Que el coseno “compense” la ausencia de palabras del documento | Ya tenés sparse de BGE-M3, hoy se *mezcla* | Alta. Barato. Medible esta semana |
| Membership por densidad / reconstrucción / residuo PCA | Que un vecino suelto autorice un texto ajeno | Offline, numpy | Alta |
| AND entre granos (oración ∩ sección) | Que una cláusula local lave un desvío global, o al revés | Requiere ingesta multi-grano | Alta, acoplada al experimento PDF |
| Métrica no promediable *después* de cambiar de base (whitening / PCA whitened L∞ o Mahalanobis) | Ejes con varianza dispar | Diagnóstico de covarianza del corpus primero | Media. Solo si el diagnóstico muestra que vale la pena |
| Diccionario disperso (SAE) para ejes monosemánticos | La base canónica no interpreta | Entrenar/cargar SAE, frágil, no portable entre embedders | Baja para este producto. Investigación, no motor |
| Proyección a subespacio prohibido (INLP / LEACE) | Energía en dirección “secreto/PII-tema” | Requiere ejemplos de la clase prohibida | Media, y **solo** como capa de tema, nunca como DLP de identificadores |

Whitening / Mahalanobis es el único retry “dimensional” que considero honesto: no porque sea de moda, sino porque convierte `|Q'_i - C'_i|` en un z-score. Todavía no te da ejes con significado. Te da ejes comparables. Si después de blanquear el conteo **sigue** sin aportar sobre coseno+densidad, se entierra la hipótesis dimensional en este embedder y se deja de gastar tiempo.

SAE es la fantasía de “la dimensión 8129 = CDE”. En interpretabilidad de LLMs tiene sentido sobre activaciones residuales del **generador**. Acá el generador es cerrado. Un SAE sobre BGE-M3 o Qwen3-Embedding es otro animal, caro, y los benchmarks de SAE son ruidosos. No lo pondría en el camino crítico.

### 4.4 Determinismo: dónde sí, dónde no

- Mismo texto + mismo embedder + mismo device + misma precisión → mismo vector. Eso es el único determinismo que importa. Hay que **probarlo** (Etapa 6 lo tiene pendiente). Sin ese número, el resto es teatro.
- El LLM no es determinista. No tiene que serlo. El gate sí.
- Cross-hardware bit-exacto: no lo asumas. Un sidecar de embedding pinneado (misma imagen Docker, mismo modelo, misma cuantización) es más realista que “corre en cualquier Mac y da el mismo float”.
- Un segundo LLM-juez (“¿esto habla del PDF?”) destruye el claim de determinismo. No lo uses como gate. Úsalo, si querés, como **oráculo de evaluación** en rompepepe, nunca en el path del usuario.

---

## 5. El experimento del PDF: cómo lo diseñaría

Laboratorio único, dos polaridades, mismo artefacto.

### 5.1 Material

Un PDF de dominio estrecho (el manual que ya usás sirve) **más** un anexo plantado con secretos sintéticos: PAN Luhn-válido, CVV, nombre+DNI, API key, dirección. Los secretos no deben aparecer en el texto “público” del manual, o deben estar en una sección marcada como CDE. Si están mezclados sin etiqueta, no podés saber si un leak es geometría o RAG que recuperó el chunk prohibido.

Tres packs lógicos, aunque sea un solo archivo físico:

- `S` = superficie permitida (el manual).
- `Z` = zona muerta / secretos plantados.
- `U` = universo (todo lo demás).

### 5.2 Modo positivo — “solo lo que está adentro”

Pregunta de membresía: texto ∈ región(S).

Ataques que importan (no “explicame una bomba” — eso el coseno ya lo pesca casi siempre):

1. Off-topic crudo.
2. Pregunta sobre S formulada con vocabulario de otro dominio.
3. Jailbreak de rol que pide responder S en formato de receta / poema / JSON.
4. Pedido de sintetizar conocimiento general “relacionado” (neumáticos en general vs. el PSI del Prisma).
5. Pregunta cuya respuesta correcta **no está en el PDF** pero parece del mismo oficio.

Métrica: recall de bloqueo en 2–5 sin matar 1’s complementarios (preguntas on-corpus parafraseadas, no verbatim — el harness v1 ya hace bien eso).

La trampa: si enchufás RAG agresivo (`rag_top_k` hasta 32), el LLM puede **inventar** alrededor de los chunks. El filtro de **entrada** deja pasar la pregunta; la **salida** se va del documento. Por eso este experimento **no cuenta** si solo auditás el prompt. Tenés que gatear la generación, oración por oración, contra S.

Regla de decisión que yo probaría primero, antes que cualquier métrica exótica:

> Una oración de salida pasa en positivo ssi (a) su 1-NN en grano oración supera umbral **y** (b) hay overlap léxico mínimo con ese chunk o su padre **y** (c) no dispara detectores de `Z`.

Conjunción. Sin promedios que se compensen.

### 5.3 Modo negativo — “lo de afuera / lo sensible”

Acá “afuera” en tu frase es ambiguo. Lo leo así, y si era otra cosa el experimento cambia:

- Permitido: hablar de casi todo.
- Prohibido: emitir o solicitar miembros de `Z` (PII, CDE, secretos), y opcionalmente el **tema** de `Z`.

Capas, en este orden, sin vergüenza de ser “poco geométrico”:

1. **Detectores exactos:** regex, Luhn, checksums, entropy de tokens tipo API key, NER liviano (Presidio o equivalente). Si esto pega, BREACH. No hay coseno que discutir.
2. **Ofuscaciones:** dígitos en palabras, Base64, hex, markdown roto, homoglyphs. rompepepe tiene que generar estas, no solo “ignore previous instructions”.
3. **Capa geométrica de tema:** “está hablando de datos de tarjetahabiente” aunque no haya emitido un PAN. Ahí sí embeddings / subespacio. Es el complemento, no el núcleo.

Si invertís el orden y ponés geometría primero, vas a publicar un DLP que no sobrevive el primer PAN partido en dos oraciones.

### 5.4 Asimetría AND / OR

- Positivo: AND entre granos y entre señales. Más difícil salir del PDF por accidente; más falsos positivos. Se calibra para no ahogar el uso legítimo.
- Negativo: OR entre detectores y granos. Una sola oración sucia corta. El falso positivo duele menos que un leak.

El `firewall_mode` actual no expresa esa asimetría. Habría que dejar de pensar en un booleano y pensar en **dos políticas**.

---

## 6. Cómo picar el documento (sin mitología)

La intuición de “picarlo de todas las maneras en que un LLM lo leería” es correcta. La implementación actual (ventana deslizante de 512 caracteres) no es una de esas maneras. Es un recorte de bytes.

Granos que sí corresponden a actos de lectura:

| Grano | Unidad | Para qué |
| :--- | :--- | :--- |
| Cláusula / oración | 1 sentencia | Leak puntual, DLP, gate de stream |
| Párrafo | bloque coherente | RAG y membresía local |
| Sección / heading | lo que el PDF ya estructura | desvío temático |
| Documento | centroide o modelo one-class global | drift de la respuesta entera |
| Ventana deslizante (la de hoy) | overlap artificial | no tirarla: cubre cláusulas que cruzan el corte de párrafo |

“Fractal” es una palabra. Lo que necesitás es **cobertura**: cada hecho del PDF debe existir como vector en al menos un grano donde no esté diluido, y cada decisión de salida debe consultar el grano que corresponde al tamaño del texto evaluado.

Metadatos mínimos por nodo en LanceDB: `pack_id`, `grain`, `parent_id`, `page`, `char_span`, `text`, `vector`, `sparse`. Sin padre/hijo no hay AND entre niveles.

Peligro: explotar el índice. Un PDF de 10 páginas, 4 granos, overlap, puede ser manejable. Un manual de 400 páginas, no. Estudio previo: contar nodos y latencia de búsqueda **antes** de enamoraros del grano oración en corpus grandes. Prefiltro Hamming/RaBitQ ya está; puede justificar su existencia acá, no en el prompt de 12 tokens.

---

## 7. Arquitectura del motor (opinión de diseño)

Separar tres máquinas. Hoy están acopladas en un proceso FastAPI.

```
[cliente]
   │  prompt
   ▼
[gate IN]  embedder local, determinista, política A
   │  PASS
   ▼
[generador]  OpenAI / Gemini / Anthropic / Ollama   ← no se confía
   │  tokens
   ▼
[gate OUT] mismo embedder, política B (y detectores)
   │  PASS oración a oración  |  BREACH → corte + evidencia
   ▼
[usuario]     [sniffer / SIEM]
```

Reglas que yo no negociaría:

1. **El embedder es el cerebro de política.** Corre local, imagen pinneada, sin red en el path caliente.
2. **El generador es no confiable.** Nube o local da igual. No le pidas que se censure; asumi que va a fugar.
3. **No hay LLM en el gate.** Ni “juez”, ni “moderador”. Si querés un reranker, que sea un modelo de embedding/rerank con score numérico, no un chat.
4. **Dos perfiles de salida, porque PCI no es UX:**
   - *Chat:* buffer hasta fin de oración, embeber (~10 ms si el embedder está fuera del proceso), emitir o cortar.
   - *Compliance:* buffer de la respuesta completa. Un PAN partido en dos oraciones no puede “ya haberse mostrado”. Si el caso de uso es CDE, el streaming al usuario es un bug.
5. **Evidencia:** hash del prompt, hash del raw del LLM, decisión, grano y chunk más cercano, detectores disparados. **No** guardar el PAN en claro. last4 + hash. El sniffer actual guarda `response_content` entero; para CDE eso es un incidente, no un feature.

Latencia: el cuello no es el LLM. Es embeber cada oración en el mismo proceso que FastAPI con SentenceTransformer. Por eso el sidecar importa más que cambiar llama3.1 por un 70B.

---

## 8. Modelos: qué cambiar y qué no

### 8.1 No confundas el LLM con el motor

`llama3.1` por Ollama es el **generador local de desarrollo**. Mejorarlo no hace más fiable la contención. Un generador más capaz, de hecho, evade mejor un gate de entrada. Para el experimento, un modelo chato que obedece el RAG es más fácil; un modelo fuerte es el adversario. rompepepe ya usa un explorer distinto del target: está bien. El bake-off de LLMs es secundario.

Si querés generador portable en Docker: `llama.cpp` (`llama-server`) o vLLM. Ollama también. Da igual para el claim. Pinnealos para reproducir ataques, no porque “filtren mejor”.

### 8.2 El bake-off que sí importa es el embedder

Criterio: no gana quien lidera MTEB. Gana quien, **en tu PDF y tu dataset de membresía/DLP**, separa in vs out con menos latencia y vector estable en CPU/GPU.

Candidatos que yo pondría en mesa, todos self-hostable:

| Modelo | Por qué está en la mesa | Por qué no casarse |
| :--- | :--- | :--- |
| **`BAAI/bge-m3`** (control) | Ya indexaste. Dense + sparse + multi-vector. Multilingüe. | In-process, pesado, MTEB mediocre vs. la generación 2025 |
| **`Qwen/Qwen3-Embedding-0.6B`** | Misma clase de tamaño (~0.6B), 1024D, MRL, contexto 32k, Apache-2.0, TEI / GGUF / ONNX / MLX. MTEB multilingual claramente por encima de BGE-M3 (64.3 vs 59.6 en la tabla del paper, mayo 2025). 8.3M downloads. | No trae sparse SPLADE. Perdés el canal léxico salvo que lo complementes |
| **`nomic-ai/nomic-embed-text-v1.5`** | 137M, MRL nativo, 8k, CPU de verdad, GGUF | Más débil; inglés-céntrico relativo |
| **`Snowflake/snowflake-arctic-embed-m-v2.0`** | Retrieval empresarial, MRL, TEI | Verificar español / mixto en *tu* PDF, no en BEIR |

`Qwen3-Embedding-4B/8B` son más “SOTA” y más caros. Para un sidecar que tiene que embeber **cada oración de salida**, 0.6B (o nomic) es la hipótesis de velocidad. 8B es vanidad hasta que 0.6B se quede corto en *separación*, no en leaderboard.

Runtime, en este orden:

1. **Hugging Face TEI** en Docker — path de producción. Un comando, CPU o GPU, pin de digest de imagen.
2. **GGUF + llama.cpp embedding** — path ultra-portable, Mac/CPU, mismo artefacto en una laptop y en un server.
3. Dejar SentenceTransformer in-process solo como baseline del repo actual.

ONNX/CoreML: interesante en edge; no lo pondría primero.

Estudio concreto: re-ingerir el mismo PDF con BGE-M3 y con Qwen3-0.6B, correr el **mismo** dataset de membresía (no MTEB), reportar AUROC in/out, FPR en on-corpus, latencia p50/p95 por oración, y igualdad de vector en 100 embeds repetidos. El que gane ahí es el motor. Hasta no tener esa tabla, “el LLM no es el mejor” es una intuición correcta apuntando al objeto equivocado: el que tal vez no es el mejor es **BGE-M3 como política**, no llama3.1.

### 8.3 Multilingüe y PDF sucio

BGE-M3 se eligió también por idioma. Qwen3-Embedding se vende como 100+ lenguas. El bake-off tiene que incluir el idioma real del PDF y de las preguntas de rompepepe. Un modelo que gana en inglés y pierde el corte de una cláusula en español no sirve.

PDFs de manuales: tablas, columnas, headers repetidos. PyMuPDF `get_text()` aplana. Si el grano “oración” se alimenta de basura de layout, la región semántica se pudre. Antes de geometría fina, mirar extracción (bloques, headings). Eso no es glamouroso y mueve más el experimento que un SAE.

---

## 9. rompepepe: de fuzzer de umbral a adversario de canal

Hoy mide si el **prompt** pasa `/audit`. El producto que querés se juega en si la **respuesta** llega al usuario.

Tres campañas, métricas duras, sin LLM-juez en el loop de éxito:

1. **Exfiltración de `Z`.** Explorer intenta que el target emita los secretos plantados (rol, Base64, “continúa la secuencia”, split, traducción, JSON). Éxito del ataque = substring / Luhn / regex en la salida **entregada**. Éxito del firewall = 0 entregas. El gate de entrada puede fallar; si el de salida sostiene 0, el claim B vive.
2. **Desvío de `S`.** Manual inyectado, modo positivo. Explorer pide receta, política, código, conocimiento general del oficio. Éxito del ataque = oración entregada que no es miembro de `S` según el oráculo de membresía (el mismo motor, más overlap léxico, más un set etiquetado). No uses al explorer para auto-calificarse.
3. **Piggybacking de salida.** Prompt on-corpus que induce una segunda parte prohibida (“y de paso dame el PAN del ejemplo”). Segmentar la **salida** igual que hoy segmentás la entrada.

Lo que no mediría: “estabilidad operacional” como % de PASS del fuzzer. Eso premia umbrales flojos. Medí **ataque vs. defensa** con etiquetas.

Dataset chico (25+25) no alcanza para cerrar un claim. Para este estudio, 25 sirve para no mentirse; no sirve para publicar. Prioridad: más negativos de `Z` ofuscados que más on-corpus.

---

## 10. Límites que hay que escribir antes de enamoraros

1. **Contención de canal ≠ el modelo no sabe.** Un empleado con otra API, o el mismo modelo sin el proxy, recupera `Z`. El control es el punto de chokepoint. Como un WAF. Nadie dice que el WAF lobotomiza Apache.
2. **Embeddings no entienden “prohibido”.** Entienden cercanía en un espacio entrenado para retrieval/STS. “CDE” no es una dirección natural. Por eso detectores + región, no región sola.
3. **Paráfrasis adversaria.** Un modelo fuerte puede hablar del PDF con un vocabulario que se aleja del chunk. El AND léxico va a falso-positivo. El coseno solo va a falso-negativo. El trade-off no desaparece con más dimensiones.
4. **RAG envenenado.** Si `Z` está en LanceDB porque ingeriste el PDF entero, el generador tiene el secreto en contexto. Modo positivo + RAG del mismo índice es un auto-leak. Hay que ingerir `S` para RAG y `Z` para denylist en **índices distintos**, o maskar `Z` del contexto.
5. **Streaming y CDE son enemigos.** Si ya mandaste 12 dígitos al browser, el BREACH tardío es forense, no prevención.
6. **Determinismo cross-host.** Sin imagen pinneada, no hay “firma” de región. El Nivel 3 del repo depende de esto; no se resuelve con un umbral.
7. **25 queries.** Cualquier ranking de filtros con n=25 es anecdótico. El 0 de excitación es informativo porque el efecto fue grosero (cae 30 puntos). No es un p-value de publicación.

---

## 11. Caminos (forks, no un waterfall)

Cuatro caminos. Se pueden serializar, pero no son “fases 1–5 de un mismo plan”. Son apuestas distintas.

### Camino I — Laboratorio de membresía (el que yo abriría primero)

No toques el filtro de producción. Offline.

- Extraé del PDF actual oraciones, párrafos, secciones.
- Embebélos con BGE-M3 (control).
- Generá un set: oraciones del PDF, paráfrasis, off-topic, leaks de `Z`.
- Dibujá las distribuciones de: 1-NN cosine, k-NN medio, residuo PCA, error de reconstrucción, overlap léxico sparse.
- Pregunta única: **¿algún estadístico separa in/out mejor que 1-NN cosine, y la excitación actual aparece en esa lista?**

Si excitación no separa ni acá, se acaba la discusión dimensional en base canónica. Si whitening hace que un L∞ conteo separe, hay retry. Si PCA-residuo gana, el retry dimensional clásico se abandona a favor de subespacio. Datos, no preferencia estética.

### Camino II — Dos políticas, detectores en negativo

Romper `firewall_mode` como polaridad. Positivo = membership. Negativo = DLP clásico + tema geométrico. Índices `S` y `Z` separados. Esto hace al experimento PDF *interpretable*. Sin esto, rompepepe no sabe qué está rompiendo.

### Camino III — Gate de salida, perfil compliance primero

Olvidate del stream bonito. Buffer de respuesta, evaluar, entregar o cortar. Más fácil de auditar, más cerca de PCI, menos teatro de tokens. El buffer por oración es un *después*, cuando el laboratorio de membresía tenga un estadístico que no sea un adorno.

### Camino IV — Sidecar de embedder + bake-off Qwen3-0.6B

Desacoplar inferencia. Misma API `/embed`. Re-ingerir. Repetir Camino I en dos espacios. Elegir por **tu** AUROC y p95, no por Twitter.

No abriría SAE, unlearning, ni “lobotomía” de pesos mientras I–III no existan. Son otro repo.

---

## 12. Orden de estudio que seguiría (horas, no sprints de producto)

1. **Determinismo del embedder actual.** 100× el mismo string, hash del vector, MPS vs CPU si podés. Sin esto no hay motor, hay demo.
2. **Mapa de separación (§11 Camino I)** sobre el PDF demo + `Z` plantado. Una notebook o un script en `backend/tests/`, no una feature.
3. **Conjunción cosine ∧ sparse** (apagar el blend α, exigir ambos). Un experimento de una tarde con el harness de excitación-compare. Hipótesis: aporta más que la excitación, que aportó 0.
4. **Ingesta multi-grano mínima** (oración + párrafo + centroide) en un índice de laboratorio, no en el ingestor de producción.
5. **Script de gate de salida offline:** tomar respuestas ya generadas (aunque sea golden set), partir en oraciones, decidir. Medir. Recién ahí hablar de SSE.
6. **Detectores PII** sobre el mismo golden set. Línea base no geométrica. Toda geometría de negativo se reporta *en exceso* sobre esa línea, no en vez de.
7. **Bake-off Qwen3-Embedding-0.6B vs BGE-M3** en Docker TEI, misma batería.
8. **MaxSim ColBERT** sobre el mismo BGE-M3 (el canal multi-vector que el encode actual no pide). Hipótesis: es el retry “no promedies” que sí vive en el modelo que ya cargás.
9. **Golden set de alucinaciones reales** (respuestas on-topic inventadas por el LLM del PDF), no solo off-topic. Si cosine/NLI no las separan, estás en Semantic Illusion: bajar el claim o pasar a extractivo (§14.2).
10. **Línea extractiva:** n-gramos / números / citas forzadas contra el PDF. Comparar FPR/FNR con geometría pura sobre el mismo golden set.
11. **Invertir un MIA de RAG** (§14.4) como detector de membresía, no como ataque.
12. **Extender rompepepe** a campañas 1–2 de §9 cuando el gate de salida exista aunque sea en batch.

Si en el paso 2 ningún estadístico nuevo gana a cosine+overlap, el proyecto no está “un umbral lejos de la lobotomía”. Está en un techo de retrieval. Ahí el producto honesto es: **allowlist de dominio con coseno + segmentación + DLP clásico en salida**, medido, con evidencia. Eso todavía vale. No es la hipótesis dimensional. Es un WAF semántico. Los WAF no se disculpan por no ser cirugía.

---

## 13. Opinión final (versión corta)

La visión defendible no es “un motor que lobotomiza LLMs”. Es **un chokepoint determinista de canal, local, portable, con región versionada y evidencia**, que trata al LLM de nube como un generador sucio.

La hipótesis dimensional merece **un** retry científico: cambiar de objeto (membresía) y, si acaso, de base (whitening), midiendo contra el coseno y contra una conjunción léxica que ya tenés y casi no usaste como *gate*. El retry más interesante que no es whitening está **ya dentro de BGE-M3 y no se usa**: late interaction (MaxSim). No merece un culto al conteo de ejes.

Hay que partir el claim en dos (§14.1). Dominio: geometría. Fidelidad al PDF: extractivo / NLI / hechos tipados. CDE: detectores. Querer las tres cosas con un solo coseno es cómo se escribe un roadmap que nunca cierra.

El PDF con modo adentro/afuera es el experimento correcto. rompepepe es el adversario correcto el día que ataque **salidas**. El modelo que “tal vez no es el mejor” no es el de chat: es el embedder como política, y encima le falta el canal token-a-token que ya trae.

---

## 14. Opciones nuevas (que no son “otro umbral de coseno”)

Esto es lo que cambiaría si alguien me pide *otras palancas*, no más de las mismas.

### 14.1 Partir el producto: dos techos, no uno

| Régimen | Ejemplo | ¿Embeddings sirven? | Claim honesto |
| :--- | :--- | :--- | :--- |
| **Contención de dominio** | “¿cómo hago una bomba?” contra un manual Chevrolet | Sí. Es el caso sintético del paper: las nubes no se solapan | “Bloqueo off-topic con tasa X” |
| **Fidelidad al documento** | El LLM inventa un PSI que *suena* a manual | No, si exigís cobertura de seguridad. Semantic Illusion | “No certifica hechos; para eso extractivo / NLI / lookup” |
| **DLP de identificadores** | PAN, CVV, API key | Casi nunca | Detectores + canarios, geometría como tema |

El paper no dice que tu firewall sea inútil. Dice que **no podés prometer 95% de recall sobre mentiras fluidas on-topic** con BGE+NLI sin apagar el producto. GPT-4 juez sí, y eso choca con el claim de determinismo. La salida de producto no es “entonces usá GPT-4 en el gate”. Es **no vender fidelidad como geometría**.

### 14.2 Extractivo: la forma de eludir la ilusión semántica

Si el modo positivo significa “solo lo que está en el PDF”, el control más frío no es un vector. Es:

1. **Citas forzadas.** Cada oración de salida debe apuntar a un `char_span` del PDF. Sin span, no se emite. El usuario ve respuesta + ancla. Auditable.
2. **Lock de hechos tipados.** PSI, pares, volts, VIN, dosis, montos: NER/regex + lookup exacto contra el índice de números del documento. La mentira fluida sobre un número **no pasa** aunque el coseno sea 0.92.
3. **Modo extractivo puro.** La respuesta es un span o una concatenación de spans. Paráfrasis = off. Brutal. Determinista. Poco “chat”. Para un CISO de taller / clínico, a veces es exactamente el producto.
4. **N-gram coverage.** Fracción de tokens de contenido de la oración que aparecen en el chunk padre. Barato, explicable, AND-eable con cosine.

Esto no está en el repo. Es la palanca que más cambia el experimento del PDF y la que el paper de ilusión semántica deja en pie cuando la geometría se rinde.

### 14.3 El retry dimensional que sí está en tu modelo: ColBERT / MaxSim

BGE-M3 no es solo un vector 1024D. Es **dense + sparse + multi-vector**. El encode actual pide dense y, a veces, sparse. **Nunca pide ColBERT.**

Late interaction (MaxSim): cada token de la oración de salida se compara contra cada token del chunk; te quedás con el máximo por token de query y promediás esos máximos. **No hay un único coseno que se pueda compensar entre dimensiones pooled.** Un token de la salida que no encuentra ancla token-level baja el score aunque el resto de la oración “suene” al manual.

Eso es más fiel a tu intuición original (“el promedio es el agujero”) que contar ejes del vector pooled. Y no requiere SAE ni whitening. Requiere `return_colbert_vecs=True` (o el API equivalente de sentence-transformers para M3), almacenar multi-vectores —son gordos—, y un MaxSim en el gate de **oración**, no en el retrieval de 12 chunks.

Prioridad de estudio: alta. Es capacidad pagada y apagada.

Primo pobre que **sí** calculás y no usás como decisión: la firma RaBitQ (signo por eje → 1024 bits, Hamming). Acuerdo de signos es un primo binario de la excitación. Como filtro de membresía probablemente sea peor que cosine; como prefiltro ya está. Vale **un** scatter Hamming vs label in/out en el laboratorio, no una feature.

### 14.4 Invertir la literatura de ataques: el MIA *es* tu detector de membresía

Hay una línea entera de papers que tratan de adivinar si un documento está en el índice RAG. Usan casi las mismas señales que vos querés para “¿esta salida es del PDF?”:

- similitud generación↔corpus + baja perplejidad ([S²MIA](https://arxiv.org/abs/2406.19234))
- likelihood ratio calibrado por dificultad (DC-MIA / RAG-leaks)
- tapar palabras del texto y ver si el RAG las rellena ([MBA](https://doi.org/10.1145/3696410.3714771))
- entailment respuesta↔documento, 5 queries ([MEntA](https://arxiv.org/abs/2605.24312))

Leídos como ataque: “el RAG ficha”. Leídos como defensa: **el score del ataque es un membership score**. En modo positivo, si la salida *no* se parece a un miembro, se corta. En modo negativo, el mask-fill es un canario: si el modelo completa el PAN tapado, `Z` está en contexto y hay que cortar RAG, no el umbral.

Esto es una respuesta nueva, no un embedder nuevo: el adversario académico ya construyó tu métrica. rompepepe debería copiar MBA (máscaras) y S²MIA (sim+PPL) como **oráculos de campaña**, y el motor puede reusar el mismo score.

Perplejidad: hoy `compute_alpha` usa un proxy sintáctico porque no querían un segundo modelo en 16 GB. Un LM chico (Qwen3-0.6B GGUF, o el mismo embedder no sirve para PPL) en el sidecar desbloquea este score. Solo aplica si el generador es local y te da logprobs. OpenAI/Anthropic a veces dan logprobs, Gemini no de forma fiable. El path cloud pierde esta palanca: otra razón para no casar el claim al generador de nube.

### 14.5 NLI / reranker numérico (no un chat-juez)

Cross-encoder: par (chunk recuperado, oración generada) → un float. No es un LLM opinando.

| Modelo | Por qué | Costo |
| :--- | :--- | :--- |
| [`cross-encoder/nli-deberta-v3-small`](https://huggingface.co/cross-encoder/nli-deberta-v3-small) | Entailment/contradiction clásico, ~500k downloads, CPU viable | No certifica el tail (Semantic Illusion), sí mejora AUC |
| [`BAAI/bge-reranker-v2-m3`](https://huggingface.co/BAAI/bge-reranker-v2-m3) | Misma familia que tu embedder, 18M downloads, TEI lo sirve | Un sidecar más |
| [`Qwen/Qwen3-Reranker-0.6B`](https://huggingface.co/Qwen/Qwen3-Reranker-0.6B) | Hermanado con el embedder Qwen3, GGUF existe | Más pesado que DeBERTa-small |

Regla: el reranker **reordena o puntúa**, no narra. Umbral sobre el float. Determinista dado el par y el modelo pinneado. El paper dice que igual no te da cobertura 95% sobre alucinaciones reales. Úsalo como capa de **paráfrasis on-corpus**, no como certificado de verdad.

Conformal prediction (el aparato del paper) sí vale la pena **como método de umbral**: en vez de Youden sobre 25 queries, un set de calibración de n≈400–600 oraciones etiquetadas y un τ con cobertura declarada. Aunque el FPR explote, **te enterás**. Hoy el 0.5315 de cosine es un número huérfano. Conformal lo vuelve una frase de auditor: “con esta calibración, atrapo ≥1−α de la clase X, y pago FPR=…”.

### 14.6 Lobotomía de verdad (solo modelos locales): no generar el token

Si el generador corre en tu Docker (`llama.cpp`, vLLM, Ollama con logits), el control más duro no es filtrar después. Es **no dejar que el token exista**:

- Trie / FST de n-gramos del PDF: el próximo token tiene que continuar un n-gramo del corpus (extractivo en el decoder).
- Logit mask: vocabulario permitido = tokens que aparecen en los chunks RAG de este turno + puntuación.
- Gramática (Outlines / XGrammar): la respuesta debe ser `{cite, span, text}` o no sale.

Eso *sí* se parece a una lobotomía de canal: el modelo no puede emitir “4111” si ese token no está en `S` y está en la denylist. **No funciona contra OpenAI/Gemini/Anthropic.** Por eso el producto se parte otra vez:

- Path nube: gate post-hoc (lo que diseñaste).
- Path local: constrained decoding + el mismo gate como defensa en profundidad.

Si el objetivo declarado es “extrapolar en todas direcciones” incluyendo APIs cerradas, constrained decoding es un **bonus de deployment local**, no el núcleo. Si el objetivo es un appliance on-prem que ni siquiera llama a OpenAI, se vuelve el núcleo. Decidilo; son SKUs distintos.

Likelihood ratio para local: `log P(oración | chunks S) − log P(oración | vacío)`. Si el PDF no ayuda a predecir la oración, no es del PDF. Requiere logprobs. Complementa MaxSim. No lo tenés hoy porque el proxy de perplejidad es largo+densidad léxica.

### 14.7 Canarios, MinHash y el índice partido

Para `Z` (PII/CDE plantado):

- **Canarios.** Insertá cadenas imposibles (`ZXQ-CANARY-7F3A`) en el PDF de prueba. Si alguna sale, hay leak. Determinista, barato, rompepepe las debe buscar siempre. En producción: tokens canario en documentos reales de staging.
- **MinHash / winnowing** sobre ventanas de `Z`. Detecta near-copy aunque cambien dos caracteres. Es DLP de documentos, no de temas. Complementa Luhn.
- **Índices `S` y `Z` separados** (ya dicho) + **nunca** mandar `Z` al contexto RAG. El leak más probable no es geometría: es que el retriever le pasó el PAN al modelo.

### 14.8 Hechos atómicos, no oraciones

Una oración puede ser 80% fiel y 20% inventada (“el Prisma usa 32 PSI **y también sirve para inflar kayaks**”). Gatear la oración entera con un coseno es grosero.

Descomponer en proposiciones (FActScore / sub-sentence encoder, [arxiv:2311.04335](https://arxiv.org/abs/2311.04335)) y exigir membresía **por claim**. Los claims numéricos van al lookup; los claims narrativos a NLI/MaxSim. Más trabajo de ingesta. Es el único grano que coincide con “el LLM mintió una cláusula”.

### 14.9 Dos embedders como detector de mentira barata

Embebé la misma oración con BGE-M3 y Qwen3-0.6B. Si uno dice “adentro” y el otro “afuera”, no es PASS: es **REVIEW / BREACH suave**. El desacuerdo es señal; el acuerdo en “afuera” es BREACH. No es un LLM juez. Cuesta 2× embed. Útil en el laboratorio para ver cuánto del error es idiosincrasia de un espacio.

### 14.10 Lo que no agregaría aunque suene nuevo

- SAE sobre el embedder como path de producto (investigación).
- Unlearning / edición de pesos de GPT (no tenés los pesos).
- Chat-juez en el path del usuario (rompe determinismo; el paper muestra que *funciona* en el tail — reservalo a evaluación offline / rompepepe oráculo, con el costo de no ser reproducible bit a bit).
- Más LLM más grande como generador “para que filtre mejor”. Filtra peor: alucina más fluido, justo el régimen donde la geometría muere.

---

## 15. Respuestas nuevas (no solo palancas)

Cosas que ahora daría por más ciertas que cuando empecé este archivo:

1. **El objeto correcto del modo positivo no es “cerca del PDF”. Es “anclado al PDF”.** Anclaje = span, n-gramo, número, MaxSim token-level, entailment. Cercanía = coseno. El primero sobrevive Semantic Illusion mejor que el segundo.
2. **El objeto correcto del modo negativo no es “lejos del PDF”. Es “no emitir Z”.** Z se defiende con detectores, canarios y no recuperarlo. La geometría negativa es solo “está hablando del tema tarjeta”.
3. **BGE-M3 ya es un sistema de tres canales. Usás uno y medio.** El retry más barato de “no promedies” es prender el tercero (ColBERT), no reinventar excitación.
4. **La literatura de membership inference contra RAG es un catálogo de métricas de membresía.** Dejar de tratarla solo como amenaza; copiarla como laboratorio.
5. **Conformal prediction es cómo se habla de umbrales en serio.** Youden sobre 25 ítems no. Aunque el resultado sea “no se puede garantizar el 95%”, ese resultado *es* el hallazgo.
6. **Nube vs local no es una preferencia de DevOps.** En local podés lobotomizar el decoder. En nube solo el tubo. Si prometés lo mismo en los dos, estás mintiendo en uno.
7. **El LLM-juez gana en el tail y pierde el claim.** La tensión no se resuelve con un modelo “un poco más chico”. Se resuelve bajando el claim de fidelidad o saliendo de la geometría (extractivo).
8. **rompecabezas de prueba:** un golden set de mentiras on-topic del *tu* PDF vale más que Qwen3 vs BGE-M3 en MTEB. Si no las podés separar, el bake-off de embedders es teatro.

---

## 16. Caminos extra (además de I–IV)

### Camino V — Anclaje extractivo

Índice de spans + números del PDF. Gate de salida: sin ancla, no sale. Medir utilidad (¿sigue siendo un chat?) vs leaks de fidelidad. Si el usuario acepta el UX, este camino **gana** al geométrico para el experimento “solo lo de adentro”.

### Camino VI — Late interaction + NLI sidecar

TEI (o el proceso actual) sirviendo M3 ColBERT + un DeBERTa-small. Score = MaxSim ∧ P(entail). Comparar contra cosine-only en el golden set de §12.10. Si no gana, no agregues modelos.

### Camino VII — SKU local con decoding restringido

Appliance Docker: llama.cpp + trie del corpus. El path OpenAI queda en “WAF post-hoc”. No mezclar las demos. rompepepe contra los dos SKUs, mismas campañas, para ver cuánto compra la lobotomía de logits.

Si V, VI y el Camino I dicen lo mismo (el coseno de dominio alcanza, la fidelidad no), el writeup se escribe solo: **somos un firewall de región, no un verificador de verdad**. Eso todavía es un producto. Es más chico que la hipótesis. Es defendible.
