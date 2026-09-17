# Pilar 2 — Ingesta fractal y pirámide en LanceDB

> Fuente: PDF, Documento 1.
> Tickets: [L03](../tickets/L03-ingesta-piramide-laboratorio.md), [L04](../tickets/L04-and-multigrano-offline.md).
> Código hoy: [`backend/app/modules/ingestor.py`](../../../backend/app/modules/ingestor.py) (`chunk_text` 512/50 chars), [`backend/app/modules/storage.py`](../../../backend/app/modules/storage.py) (tabla `knowledge`, metadata `filename` + `chunk_index`).

---

## El problema del chunker ciego

Ventana fija de 512 caracteres con overlap 50:

- **Dilución.** Una inyección de ~20 palabras dentro de 512 chars benignos se promedia en el embedding.
- **Fractura.** Cortar por bytes parte cláusulas numéricas (torques, presiones) a la mitad → vectores espurios.
- **Asimetría de escala.** Un prompt o una oración generada (15–40 tokens) no se compara limpio contra un bloque de ~120 tokens.

---

## Pirámide de 4 granos

| Nivel | `grain` | Unidad | Rango típico | Función |
| :--- | :--- | :--- | :--- | :--- |
| 1 Micro | `sentence` | Cláusula / oración | 15–40 tokens | Inspección de egreso; inyecciones quirúrgicas |
| 2 Meso | `paragraph` | Párrafo coherente | 256–512 tokens | RAG y coherencia local |
| 3 Macro | `section` | Sección / capítulo | 2.000–4.000 tokens | Deriva temática en docs largos |
| 4 Global | `document` | Centroide del documento | corpus del pack | Envolvente del dominio permitido |

PDFs demo: `backend/demo_corpus/automotive_maintenance.pdf`, `backend/demo_corpus/medical_hypertension.pdf`.

---

## Schema de linaje (laboratorio)

Cada vector lleva punteros de árbol. Campos mínimos (PDF):

```python
schema = {
    "node_id": str,       # id único del nodo
    "pack_id": str,       # corpus versionado
    "grain": str,         # "sentence" | "paragraph" | "section" | "document"
    "parent_id": str,     # párrafo padre (para grain=sentence)
    "section_id": str,    # sección contenedora
    "page": int,          # página del PDF fuente
    "char_span": [int, int],
    "text": str,
    "vector": list[float],  # 1024D BGE-M3 / TEI
    "sparse": dict,         # pesos léxicos SPLADE/BM25
}
```

Hoy `rabitq_schema` no tiene ninguno de esos campos de linaje. L03 crea una **tabla aparte** (no migrar `knowledge` en ese ticket). Se pueden conservar `vector_packed` / RaBitQ si el insert reusa `_enrich_node()`; no es el objetivo del pilar.

---

## Regla AND multi-grano (modo positivo)

Una oración generada no pasa por cercanía a un chunk aislado. Conjunción:

1. **Proximidad micro.** Distancia válida contra un nodo `grain=sentence`.
2. **Validación meso.** El párrafo padre (`parent_id`) coincide con el contexto recuperado.
3. **Coherencia léxica.** Overlap mínimo de términos (sparse) con el documento fuente.

Sin promedio que compense un grano con otro.

---

## MRL (nota, no ticket)

Los primeros 64/128 componentes de un embedding Matryoshka pueden prefiltrar (Hamming/RaBitQ ya existe en el insert). La verificación fina de la cláusula usa el vector completo. No hay ticket MRL: es complemento de L03/L05 cuando el runtime lo exponga. No cambiar de modelo en este pack.
