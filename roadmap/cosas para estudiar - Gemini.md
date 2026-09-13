# Cosas para estudiar — Caminos hacia una Contención Dimensional y Bidireccional Determinista

> **Documento de Investigación y Arquitectura Prospectiva**  
> **Autor / Perspectiva:** Gemini  
> **Ubicación:** `roadmap/cosas para estudiar - Gemini.md`  
> **Contexto:** Segunda fase del Three-Headed Semantic Firewall: rescate de la hipótesis dimensional, inspección bidireccional (entradas y salidas), chunking fractal/multi-escala, optimización de modelos de embedding locales y validación con `rompepepe`.

---

## 1. La Visión: Contención Determinista e Inspección Bidireccional

El objetivo es transformar el firewall en un **motor de contención ontológica estricta ("lobotomía geométrica")** que actúe como un proxy perimetral de dos vías entre el usuario y el LLM:

```
                               ┌─────────────────────────────────────────┐
                               │             USUARIO / CLIENTE           │
                               └───────┬─────────────────────────▲───────┘
                                       │                         │
                                1. Prompt                 4. Respuesta Verificada
                                       │                         │  o Alerta [BREACH]
                                       ▼                         │
                         ┌─────────────────────────────────────────────┐
                         │      SEMANTIC FIREWALL BIDIRECCIONAL        │
                         │                                             │
                         │  [Entrada]                        [Salida]  │
                         │  • Segmentación                   • Buffer  │
                         │  • Espacio Habilitado             • Oración │
                         │    o Prohibido                    • Espacio │
                         └─────┬─────────────────────────────▲─────────┘
                               │ (PASS)                      │
                               │                             │ 3. Raw Output
                               ▼                             │    del LLM
                         ┌───────────────────────────────────┴─────────┐
                         │   LLM (OpenAI / Gemini / Anthropic / Local) │
                         └─────────────────────────────────────────────┘
```

### Casos de Uso Reales
1. **Modo Positivo Estricto (Soberanía Documental):**
   * El LLM solo tiene permitido hablar de lo que está **adentro** del PDF suministrado.
   * Si el usuario pide: *"Explicame cómo hacer una bomba"* o *"¿Quién ganó el mundial?"*, el firewall de entrada lo bloquea.
   * Si el usuario logra eludir la entrada con un jailbreak sofisticado y el LLM empieza a responder algo ajeno al documento, **el firewall de salida intercepta la respuesta en el vuelo y la aborta**.
2. **Modo Negativo Estricto (DLP de Datos Sensibles / PII / CDE):**
   * El espacio prohibido almacena coordenadas de información clasificada, credenciales, secretos industriales, números de tarjeta o PII.
   * Si cualquier generación del LLM roza ese espacio prohibido, se corta la transmisión inmediatamente y se genera una traza de auditoría con evidencia forense inmutable.

---

## 2. Rescatando la Hipótesis Dimensional: ¿Por qué falló antes y cómo resolverla?

La intuición original (medir diferencias eje por eje en lugar de un coseno promediado) tiene un fundamento teórico intuitivo: **el coseno es un ángulo global ciego a compensaciones ortogonales**. Sin embargo, la implementación original (`|Q_i - C_i| <= 0.005`) falló empíricamente por tres problemas matemáticos clásicos del Procesamiento de Lenguaje Natural:

### Las Tres Barreras de la Implementación Original
1. **Anisotropía de los Espacios Latentes:** En los Transformers (como BGE-M3), los embeddings sufren de colapso cónico. No ocupan una esfera uniforme; se concentran en un cono hiperdimensional estrecho.
2. **Varianza Desigual por Eje:** Ciertas dimensiones tienen varianzas enormes (actúan como sesgos sintácticos o de frecuencia de tokens), mientras que otras casi no varían. Exigir la misma tolerancia escalar `0.005` en las 1024 dimensiones castiga a las dimensiones ruidosas y relaja absurdamente a las silenciosas.
3. **Representaciones Polisémicas y Distribuidas:** En un embedding denso convencional, **la dimensión 42 no significa "PII" ni "presión de neumáticos"**. Los conceptos no viven alineados a la base canónica cartesiana; viven en *combinaciones lineales* de múltiples ejes.

---

### Caminos para Lograr Determinismo Dimensional Real

#### Camino A: Normalización por Covarianza y Distancia de Mahalanobis
En lugar de medir la distancia euclidiana por eje `|Q_i - C_i|`, se utiliza la matriz de covarianza $\Sigma$ del corpus:

$$D_M(Q, C) = \sqrt{(Q - C)^T \Sigma^{-1} (Q - C)}$$

O mediante **Blanqueamiento (Embedding Whitening)**:
* Se calcula la descomposición SVD o PCA del corpus: $W = \Sigma^{-1/2}$.
* Se proyectan los vectores a un espacio esferizado: $Q' = (Q - \mu) W$.
* **En el espacio blanqueado, todas las dimensiones tienen varianza 1 y covarianza 0.** Aquí, la diferencia dimensional por componente $|Q'_i - C'_i|$ es estadísticamente rigurosa (mide desviaciones estándar reales z-score).

#### Camino B: Sparse Autoencoders (SAE) y Diccionarios de Monosemanticidad
Esta es la vanguardia de la interpretabilidad moderna (investigada por Anthropic y OpenAI).
* Se entrena o utiliza un autoencoder disperso (SAE) que proyecta el vector 1024D a un espacio de alta dimensión disperso (ej. 8.192 o 16.384 dimensiones) con penalización $L_1$.
* En este espacio, las dimensiones **sí son monosemánticas** (una dimensión representa "datos personales", otra "insultos", otra "frenos automotrices").
* **Determinismo absoluto:** Si la dimensión del concepto prohibido tiene activación $> 0$, se dispara el bloqueo instantáneo con explicabilidad total.

#### Camino C: Concept Erasure y Subespacios Nulos (RLACE / INLP)
* Si se define un espacio prohibido $P$ (ej. PII o contenido peligroso), se halla el subespacio vectorial de esas amenazas mediante proyecciones ortogonales (*Iterative Nullspace Projection*).
* Para cualquier vector de salida $Y$ del LLM, se calcula su proyección en el subespacio prohibido:
  $$\| \Pi_P(Y) \|^2 > \tau$$
* Si la energía proyectada en el subespacio prohibido supera el umbral $\tau$, la salida queda vetada de forma determinista.

#### Camino D: Matryoshka Representation Learning (MRL)
* Utilizar embeddings entrenados explícitamente con pérdida Matryoshka (como `nomic-embed-text-v1.5` o `bge-m3` con truncado adaptativo).
* Los primeros $D$ componentes ($D=64, 128, 256$) concentran los aspectos semánticos más densos y discriminativos, permitiendo un filtrado jerárquico por cascada.

---

## 3. Mapeo del Espacio Semántico: Chunking Fractal / Multi-Escala

Para encapsular con precisión un documento (para saber si una salida o entrada está "dentro" o "fuera"), un tamaño de chunk único (ej. 512 caracteres) es insuficiente. Si el chunk es muy chico, se pierde el contexto global. Si es muy grande, se diluye la señal de una cláusula específica.

### La Solución: Pirámide de Granularidad Semántica

```
  [ Nivel 4: Documento Completo ]  ──▶ Centroide / Envolvente Global
                 ▲
  [ Nivel 3: Capítulos / Secciones ] ──▶ Macro-regiones temáticas (~2000-4000 tokens)
                 ▲
  [ Nivel 2: Párrafos Coherentes ]  ──▶ Unidades RAG estándar (~256-512 tokens)
                 ▲
  [ Nivel 1: Cláusulas / Oraciones ] ──▶ Micro-coordenadas deterministas (~15-40 tokens)
```

### Mecánica de Ingesta en LanceDB:
1. **Micro-Chunks (Oración/Cláusula):** Máxima resolución. Permite detectar inyecciones quirúrgicas o fugas puntuales de una línea de texto.
2. **Meso-Chunks (Párrafos):** Almacenan contexto y se usan para el retrieval RAG hacia el LLM.
3. **Macro-Chunks / Centroides:** Definen la envolvente convexa (*Convex Hull*) o hiperesfera delimitadora del documento completo.
4. **Relación Jerárquica:** Cada micro-chunk en LanceDB contiene metadatos de su párrafo padre y su capítulo padre.
5. **Decisión de Pertenencia:**
   * Un texto generado por el LLM se segmenta en oraciones.
   * Cada oración debe encontrar un vecino cercano en el nivel micro o meso que satisfaga la distancia calibrada. Si una sola oración de la respuesta cae en el vacío semántico, se marca la alerta.

---

## 4. Modelos de Embedding y Motores Locales en Docker

Para que este motor sea portable, ultra-rápido (<15ms por evaluación) y corra dentro de un contenedor Docker en una máquina estándar sin depender de hardware exótico:

### Servidores y Runtimes Recomendados (Infraestructura)

| Servidor / Runtime | Lenguaje | Características | Caso de Uso |
| :--- | :--- | :--- | :--- |
| **Hugging Face TEI** *(Text Embeddings Inference)* | Rust | • Sub-milisegundo en CPU/GPU<br>• FlashAttention, paged attention<br>• Cuantización nativa (int8, float16)<br>• Imagen Docker oficial de 1 comando | **La mejor opción para Docker de producción.** |
| **Infinity** | Python / Rust | • Async de alto rendimiento<br>• Soporte de múltiples modelos simultáneos<br>• Compatible con PyTorch, ONNX y TensorRT | Excelente alternativa flexible para entornos Python. |
| **ONNX Runtime (CPU/CoreML)** | C++ / Python | • Cero dependencias pesadas de PyTorch<br>• Modelos cuantizados en formato `.onnx` | Ideal para despliegues ultra-ligeros (edge / sidecars). |

### Comparativa de Modelos de Embedding para esta Tarea

| Modelo | Dimensión | Contexto | Puntos Fuertes | Consideración para este Proyecto |
| :--- | :---: | :---: | :--- | :--- |
| **`nomic-ai/nomic-embed-text-v1.5`** | 768D (MRL: 64D–768D) | 8.192 tokens | • Matryoshka nativo<br>• Contexto largo (permite chunks de capítulos enteros)<br>• Muy liviano y rápido | **Candidato #1** para experimentar con dimensionalidad variable y chunks jerárquicos. |
| **`BAAI/bge-m3`** *(Actual)* | 1024D | 8.192 tokens | • Multilingüe de primer nivel<br>• Dense + Sparse (SPLADE) + Multi-vector | Excelente, pero requiere exprimir su canal sparse y correr en TEI para ganar velocidad. |
| **`Snowflake/snowflake-arctic-embed-m-v2.0`** | 768D (MRL) | 8.192 tokens | • Líder en benchmarks de retrieval empresarial<br>• Calibración nítida para OOD | Muy robusto para separar temas técnicos de temas generales. |
| **`answerdotai/ModernBERT-embed`** | 768D | 8.192 tokens | • Arquitectura moderna (2024/2025)<br>• Velocidad extrema en CPU gracias a FlashAttention nativo | Gran candidato para minimizar latencia en CPUs estándar. |

---

## 5. Arquitectura del Filtrado de Salida (Nivel 2 Bidireccional)

Filtrar la salida del LLM presenta un desafío de ingeniería crucial: **el streaming**. No queremos esperar 10 segundos a que el LLM termine de generar toda la respuesta antes de empezar a evaluarla.

### Estrategia de Evaluación en Vuelo: *Speculative Sentence Buffering*

```
LLM Stream de Tokens:
"El procedimiento..." ──▶ [Acumulador de Tokens]
"...requiere calibrar..." ──▶ [Espera signo de puntuación: . ; \n]
"...el sensor a 32 PSI." ──▶ Cláusula Completa (Oración 1)
                                      │
                                      ├──▶ [Async Embedder <10ms]
                                      │           │
                                      │           ├── [Pasa]: Liberar stream al usuario
                                      │           └── [Breach]: Abortar conexión, emitir
                                      │                         bloqueo y loguear auditoría.
```

1. **Buffer de Oración:** Se acumulan tokens hasta completar una unidad con sentido (delimitada por signos de puntuación o saltos de línea).
2. **Evaluación Instantánea:** La oración se envía al runtime de embedding local (TEI en ~5-10ms).
3. **Liberación Condicional:**
   * Si la oración está dentro del espacio habilitado (modo positivo) o lejos del espacio prohibido (modo negativo), se libera al cliente.
   * Si detecta una desviación dimensional o violación de espacio, **se corta el SSE en el acto**, reemplazando el texto restante por un mensaje de intervención de seguridad y guardando la evidencia en el Sniffer.

---

## 6. Validación Continua y Fuzzing con `rompepepe`

Para probar si la contención dimensional y el filtrado bidireccional realmente "lobotomizan" o blindan al LLM, `rompepepe` debe evolucionar de un fuzzer de entrada a un **adversario de dos vías**:

### Protocolo de Ataque para `rompepepe`
1. **Prueba de Fuga de PII / Secreto (Salida Negativa):**
   * Configurar el espacio prohibido con datos sensibles inventados (ej. claves de API maestras o números de seguro social dentro del documento de prueba).
   * Instruir al Explorer LLM de `rompepepe` para usar jailbreaks (roleplay, codificación base64, hipotéticos) intentando que el LLM del firewall emita esos datos.
   * **Métrica de éxito:** El firewall de salida debe capturar el 100% de los intentos de emisión, independientemente de si el prompt logró engañar al LLM.
2. **Prueba de Desvío Temático (Salida Positiva):**
   * Ingestar un manual técnico (ej. Chevrolet Prisma).
   * Atacar al sistema pidiéndole que explique una receta de cocina o poesía política, intentando que el LLM la genere camuflada como metáforas automotrices.
   * Evaluar si la pirámide de chunks y la distancia dimensional rechazan la respuesta generada.

---

## 7. Plan de Acción y Roadmap de Estudio Priorizado

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ FASE 1: Diagnóstico Matemático del Espacio Actual                           │
│ • Analizar varianza y correlación entre las 1024D de BGE-M3 en LanceDB.      │
│ • Probar Blanqueamiento (Whitening / Mahalanobis) en benchmark offline.      │
├─────────────────────────────────────────────────────────────────────────────┤
│ FASE 2: Ingesta Fractal / Multi-Escala                                      │
│ • Modificar ingestor.py para indexar a nivel Documento, Párrafo y Oración.   │
│ • Guardar metadatos jerárquicos en LanceDB.                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│ FASE 3: Motor Dockerizado de Alta Velocidad (TEI / Infinity)                │
│ • Crear docker-compose.yml con Hugging Face TEI (BGE-M3 o Nomic Embed).     │
│ • Desacoplar la inferencia del proceso Python de FastAPI.                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ FASE 4: Proxy Bidireccional de Salida (Nivel 2)                             │
│ • Implementar Speculative Sentence Buffering en el stream de chat.py.        │
│ • Gating en tiempo real de los tokens salientes antes de llegar al usuario. │
├─────────────────────────────────────────────────────────────────────────────┤
│ FASE 5: Red-Teaming y Batería de Pruebas con Rompepepe                      │
│ • Ejecutar campañas de jailbreak orientadas a forzar fugas de salida.       │
│ • Medir precisión, recall y latencia añadida al stream.                     │
└─────────────────────────────────────────────────────────────────────────────┘
```
