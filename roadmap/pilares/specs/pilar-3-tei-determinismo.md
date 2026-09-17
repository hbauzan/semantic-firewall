# Pilar 3 — Determinismo numérico y sidecar TEI

> Fuente: PDF, Documento 2.
> Tickets: [L01](../tickets/L01-determinismo-embedder-actual.md), [L05](../tickets/L05-sidecar-tei.md).
> Código hoy: [`backend/app/modules/embedder.py`](../../../backend/app/modules/embedder.py), [`backend/app/modules/mlx_embedder.py`](../../../backend/app/modules/mlx_embedder.py), [`backend/app/modules/dispatcher.py`](../../../backend/app/modules/dispatcher.py). Sin Docker/TEI. `setup-fw.sh` declara que Docker no se usa.

---

## El problema

En perímetro de seguridad el mismo texto + el mismo modelo tiene que dar el mismo vector. En PyTorch / Transformers in-process eso se rompe:

1. **Suma no asociativa (IEEE 754).** \((a+b)+c \neq a+(b+c)\). El orden de reducción de kernels cambia los últimos decimales.
2. **Paralelismo no determinista (CUDA / MPS).** `atomicAdd` y el orden de hilos dependen de la carga. Diez embeds del mismo string varían en los decimales 5–6.
3. **Deriva de librerías.** PyTorch, CUDA, cuDNN, BLAS, FMA sí/no: distintas instrucciones, distinto float.

### Impacto

Si \(\tau = 0.750000\), un entorno de test que da `0.750002` y uno de prod que da `0.749998` convierte un bloqueo en fuga (o al revés). Un vector no reproducible invalida la evidencia.

L01 **mide** este fenómeno en el ST actual (solapa Etapa 6 Bloque A). L05 **cambia el runtime**.

---

## Solución: TEI en sidecar

```
[FastAPI]  -- HTTP/gRPC local (<5 ms) -->  [TEI container, Rust]
```

Propiedades exigidas por el PDF:

1. Binario nativo (Rust / Candle / FlashAttention). Sin intérprete Python en el path de embed.
2. Imagen por **digest inmutable**: `ghcr.io/huggingface/text-embeddings-inference@sha256:…`. Prohibido `tei:latest`.
3. Cuantización y kernels fijos en el contenedor (float16 o int8, declarado).
4. Latencia objetivo del PDF: &lt; 5 ms/oración CPU, &lt; 1 ms GPU.

El adapter habla la misma interfaz que hoy (`EmbeddingOutput` dense + sparse si el modelo lo da). El dispatcher deja de llamar SentenceTransformer cuando TEI está configurado.

---

## Configuración

- URL y digest por env (`.env.example` del backend). Secrets nunca en git.
- Fallback: ST in-process hasta el corte explícito de L05 (tests sin Docker).
- `setup-fw.sh` y README de arranque deben dejar de decir que Docker no se usa, **cuando L05 cierre**.

Determinismo de este pilar = reproducibilidad **dentro de la imagen pinneada**. No se promete bit-exacto Mac MPS vs NVIDIA fuera de ese contenedor.
