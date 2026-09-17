# Alcance de este pack

Fecha: 2026-09-17. Cubre **solo** lo condensado en el PDF de 4 pilares.

---

## Qué hay que construir

1. **Geometría (Pilar 1 / Parte 2.1).** Blanquear el espacio del corpus \(Q' = (Q-\mu)\Sigma^{-1/2}\) para que una diferencia por eje sea un z-score. Aislar el subespacio prohibido \(P\) (INLP) y cortar si \(\|\Pi_P(Y)\|^2 > \tau\), con \(\tau\) calibrado empíricamente (100 prompts benignos + 100 evasiones) vía rompepepe.
2. **Ingesta fractal (Documento 1).** Dejar de picar por 512 caracteres. Pirámide de 4 granos (oración, párrafo, sección, documento) en LanceDB con linaje (`parent_id`, `char_span`, `page`). Decisión en modo positivo por **conjunción** micro ∩ meso ∩ léxico.
3. **TEI (Documento 2).** Sacar el embedder del proceso Python. Sidecar Hugging Face Text Embeddings Inference, imagen pinneada por digest SHA256, para reproducir vectores en el perímetro.
4. **rompepepe bidireccional (Documento 3).** Tres campañas (exfiltración de Z, desvío de S, piggyback/fragmentación). Explorer genera ataques; Oracle puntúa la brecha sobre lo **entregado**. Métricas: recall de bloqueo, FPR, egress leakage. No % PASS operacional.
5. **Egreso dual-profile (Documento 4).** Perfil Chat: speculative sentence buffering. Perfil Compliance/CDE: retener la respuesta completa y auditar las 4 capas (DLP rígido, anti-homoglifos, subespacios, verificación de números) antes de soltar un token al usuario.

---

## Claim de este pack

Perímetro determinista (mismo texto + mismo embedder pinneado → mismo vector en ese runtime) con inspección **bidireccional**: el prompt y la generación se pueden cortar. El LLM de nube o local es un generador; la política vive en el firewall.

---

## Qué no entra (otra etapa)

Cualquier palanca que el PDF no promovió. No la implementes. No la documentes acá. No la “dejes lista”. Otra etapa, otro pack.

El Oracle de rompepepe evalúa campañas. No es un LLM-juez en el path del usuario.

---

## Hoy vs destino

| Pieza | Hoy | Destino de este pack |
| :--- | :--- | :--- |
| Ingesta | `chunk_text` 512/50 chars, un grano | 4 granos + linaje |
| LanceDB | `knowledge` plano (`filename`, `chunk_index`) | schema con `grain`, `parent_id`, `char_span`, `page` |
| Embedder | SentenceTransformer in-process, BGE-M3 | sidecar TEI, digest pinneado |
| Gate | entrada only; cosine / excitation / noise | blanqueamiento + INLP en lab → luego egreso |
| Egreso | stream crudo al cliente | dual-profile Chat / Compliance |
| rompepepe | `POST /audit`, % PASS | `/chat` + Oracle + 3 campañas |
