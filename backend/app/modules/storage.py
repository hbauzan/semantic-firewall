import hashlib
import json
import lancedb
from lancedb.pydantic import Vector, LanceModel
import logging
import os
import re
from typing import Any

import numpy as np
import pyarrow as pa

from app.core.settings import settings

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "lancedb_data")

_SAFE_FILENAME_RE = re.compile(r'^[\w\s.\-()]+$', re.UNICODE)

RABITQ_VECTOR_DIM = 1024
RABITQ_PACKED_BYTES = 128

rabitq_schema = pa.schema([
    pa.field("id", pa.int64()),
    pa.field("vector", pa.list_(pa.float32(), RABITQ_VECTOR_DIM)),
    pa.field("vector_packed", pa.list_(pa.uint8(), RABITQ_PACKED_BYTES)),
    pa.field("centroid_distance", pa.float32()),
    pa.field("quantization_projection", pa.float32()),
    pa.field("sparse_lexical", pa.string()),
    pa.field("text", pa.string()),
    pa.field("metadata", pa.string()),
])


class KnowledgeNode(LanceModel):
    """LanceDB row model — includes RabitQ binary signature and sparse lexical fields."""

    id: int
    vector: Vector(1024)
    vector_packed: list[int] | None = None
    centroid_distance: float | None = None
    quantization_projection: float | None = None
    sparse_lexical: str | None = None
    text: str
    metadata: str


def serialize_sparse(sparse: dict[int, float] | None) -> str | None:
    """JSON-encode sparse lexical weights for LanceDB storage."""
    if not sparse:
        return None
    return json.dumps({str(k): v for k, v in sparse.items()})


def deserialize_sparse(raw: str | dict | None) -> dict[int, float] | None:
    """Decode sparse lexical weights from stored JSON."""
    if raw is None:
        return None
    if isinstance(raw, dict):
        return {int(k): float(v) for k, v in raw.items()}
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(parsed, dict):
        return None
    return {int(k): float(v) for k, v in parsed.items()}


def pack_binary_signature(vector: np.ndarray | list[float]) -> bytes:
    """Project 1024D floats to a 1024-bit signature packed in 128 uint8 bytes."""
    arr = np.asarray(vector, dtype=np.float32).ravel()
    if arr.size < RABITQ_VECTOR_DIM:
        padded = np.zeros(RABITQ_VECTOR_DIM, dtype=np.float32)
        padded[: arr.size] = arr
        arr = padded
    else:
        arr = arr[:RABITQ_VECTOR_DIM]

    bits = (arr >= 0.0).astype(np.uint8)
    packed = np.packbits(bits)
    if packed.size < RABITQ_PACKED_BYTES:
        out = np.zeros(RABITQ_PACKED_BYTES, dtype=np.uint8)
        out[: packed.size] = packed
        return out.tobytes()
    return packed[:RABITQ_PACKED_BYTES].tobytes()


def _hamming_popcount_fallback(a: bytes, b: bytes) -> int:
    dist = 0
    for x, y in zip(a, b):
        dist += (x ^ y).bit_count()
    return dist


def hamming_distance(a: bytes, b: bytes) -> int:
    """CPU Hamming distance over packed binary signatures (SimSIMD optional)."""
    if len(a) != len(b):
        length = min(len(a), len(b))
        a, b = a[:length], b[:length]

    try:
        import simsimd  # type: ignore[import-untyped]

        arr_a = np.frombuffer(a, dtype=np.uint8)
        arr_b = np.frombuffer(b, dtype=np.uint8)
        return int(simsimd.hamming(arr_a, arr_b))
    except (ImportError, AttributeError, TypeError, ValueError):
        return _hamming_popcount_fallback(a, b)


def compute_rabitq_fields(vector: list[float]) -> dict[str, Any]:
    """Asymmetric RabitQ correction scalars for a dense vector."""
    arr = np.asarray(vector, dtype=np.float32)
    packed = list(pack_binary_signature(arr))
    signed = np.where(arr >= 0.0, 1.0, -1.0)
    centroid_distance = float(np.linalg.norm(arr))
    quantization_projection = float(np.dot(arr, signed) / (np.linalg.norm(signed) + 1e-9))
    return {
        "vector_packed": packed,
        "centroid_distance": centroid_distance,
        "quantization_projection": quantization_projection,
    }


def _normalize_row(row: dict) -> dict:
    """Attach deserialized sparse_lexical for API consumers."""
    out = dict(row)
    sparse = deserialize_sparse(row.get("sparse_lexical"))
    if sparse is not None:
        out["sparse_lexical"] = sparse
    return out


class Storage:
    def __init__(self):
        self.db = lancedb.connect(DB_PATH)
        self.table_name = "knowledge"
        self.hamming_prefilter_max = settings.hamming_prefilter_max
        self.rabitq_w = settings.rabitq_w

        existing = self.db.list_tables()
        table_list = existing.tables if hasattr(existing, 'tables') else list(existing)
        if self.table_name not in table_list:
            self.table = self.db.create_table(
                self.table_name,
                schema=rabitq_schema,
                mode="create",
            )
        else:
            self.table = self.db.open_table(self.table_name)
            self._ensure_schema_compatibility()

    def _ensure_schema_compatibility(self):
        """Ensure all fields defined in rabitq_schema exist in the table on disk."""
        existing_fields = set(self.table.schema.names)
        missing_fields = [f for f in rabitq_schema if f.name not in existing_fields]
        if missing_fields:
            missing_names = [f.name for f in missing_fields]
            logger.info("Migrating LanceDB table schema: adding missing fields %s", missing_names)
            self.table.add_columns(missing_fields)

    def _enrich_node(self, node: dict) -> dict:
        """Attach binary signature fields when missing."""
        enriched = dict(node)
        if "vector_packed" not in enriched or enriched.get("vector_packed") is None:
            rabitq = compute_rabitq_fields(enriched["vector"])
            enriched.update(rabitq)
        sparse = enriched.get("sparse_lexical")
        if isinstance(sparse, dict):
            enriched["sparse_lexical"] = serialize_sparse(sparse)
        return enriched

    def add_nodes(self, nodes: list[dict]):
        """Insert nodes with RabitQ binary signatures."""
        if nodes:
            enriched = [self._enrich_node(dict(n)) for n in nodes]
            self.table.add(enriched)

    def get_max_id(self) -> int:
        if self.table.count_rows() == 0:
            return 0
        rows = self.table.search().select(["id"]).to_list()
        return max(row["id"] for row in rows)

    def search_nearest(self, query_vector: list[float], k: int = 1):
        if self.table.count_rows() == 0:
            return []

        oversample = min(max(k * 4, k), self.table.count_rows())
        results = self.table.search(query_vector, vector_column_name="vector").limit(oversample).to_list()
        return self._hamming_prefilter(query_vector, results, k=k)

    def resolve_active_pack(self, active_corpus_file: str | None = None) -> str | None:
        """Resolve which pack scopes firewall/RAG search."""
        packs = self.get_summary()
        pack_names = {p["filename"] for p in packs}
        if active_corpus_file and active_corpus_file in pack_names:
            return active_corpus_file
        if len(packs) == 1:
            return packs[0]["filename"]
        return None

    def search_for_firewall(
        self,
        query_vector: list[float],
        *,
        k: int,
        active_corpus_file: str | None = None,
    ):
        """Pack-scoped nearest-neighbor search with Hamming pre-filter."""
        pack = self.resolve_active_pack(active_corpus_file)
        if pack:
            return self.search_nearest_for_pack(query_vector, pack, k=k)
        return self.search_nearest(query_vector, k=k)

    def _composite_score(self, hamming_dist: int, row: dict) -> float:
        """Lower is better — Hamming distance minus RaBitQ projection bonus."""
        projection = float(row.get("quantization_projection") or 0.0)
        return float(hamming_dist) - self.rabitq_w * projection

    def _hamming_prefilter(
        self,
        query_vector: list[float],
        candidates: list[dict],
        *,
        k: int,
    ) -> list[dict]:
        """Discard candidates whose binary signature is too far in Hamming space."""
        if not candidates:
            return []

        query_packed = pack_binary_signature(query_vector)
        scored: list[tuple[float, dict]] = []
        discarded = 0
        for row in candidates:
            packed = row.get("vector_packed")
            if packed is None:
                scored.append((0.0, row))
                continue
            if isinstance(packed, list):
                packed_bytes = bytes(packed[:RABITQ_PACKED_BYTES])
            else:
                packed_bytes = bytes(packed)
            dist = hamming_distance(query_packed, packed_bytes)
            if dist <= self.hamming_prefilter_max:
                scored.append((self._composite_score(dist, row), row))
            else:
                discarded += 1

        if discarded:
            logger.info(
                "Hamming prefilter discarded %d/%d candidates (max=%d)",
                discarded, len(candidates), self.hamming_prefilter_max,
            )

        if not scored:
            return [_normalize_row(r) for r in candidates[:k]]

        scored.sort(key=lambda item: item[0])
        return [_normalize_row(row) for _, row in scored[:k]]

    def search_nearest_for_pack(self, query_vector: list[float], filename: str, k: int = 1):
        """Nearest-neighbor search limited to vectors from a single pack."""
        if self.table.count_rows() == 0:
            return []

        if not filename or not _SAFE_FILENAME_RE.match(filename):
            logger.warning("Rejected unsafe filename for pack search: %r", filename)
            return []

        safe_name = filename.replace("'", "''")
        filter_str = f"metadata LIKE '%\"filename\": \"{safe_name}\"%'"
        oversample = min(max(k * 4, k), self.table.count_rows())
        try:
            results = (
                self.table.search(query_vector, vector_column_name="vector")
                .where(filter_str)
                .limit(oversample)
                .to_list()
            )
            filtered = self._hamming_prefilter(query_vector, results, k=k)
            return filtered if filtered else [_normalize_row(r) for r in results[:k]]
        except Exception as e:
            logger.warning("Pack-scoped search failed, falling back to global: %s", e)
            return self.search_nearest(query_vector, k=k)

    def count_rows(self) -> int:
        return self.table.count_rows()

    def iter_all_rows(self) -> list[dict]:
        """Return all rows for backfill utilities."""
        if self.table.count_rows() == 0:
            return []
        return self.table.search().to_list()

    def get_summary(self) -> list[dict]:
        if self.table.count_rows() == 0:
            return []

        rows = self.table.search().select(["metadata"]).to_list()

        packs = {}
        for row in rows:
            try:
                m = json.loads(row.get("metadata", "{}"))
                fname = m.get("filename", "unknown")
                packs[fname] = packs.get(fname, 0) + 1
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning("Malformed metadata entry: %s", e)

        return [{"filename": k, "chunks": v} for k, v in packs.items()]

    def delete_pack(self, filename: str):
        if self.table.count_rows() == 0:
            return

        if not filename or not _SAFE_FILENAME_RE.match(filename):
            logger.warning("Rejected unsafe filename for deletion: %r", filename)
            raise ValueError(f"Invalid filename: contains disallowed characters")

        safe_name = filename.replace("'", "''")
        filter_str = f"metadata LIKE '%\"filename\": \"{safe_name}\"%'"
        self.table.delete(filter_str)

    def _pack_rows(self, filename: str) -> list[dict]:
        """Return all rows whose metadata matches ``filename``."""
        if self.table.count_rows() == 0:
            return []
        if not filename or not _SAFE_FILENAME_RE.match(filename):
            logger.warning("Rejected unsafe filename for pack read: %r", filename)
            return []

        safe_name = filename.replace("'", "''")
        filter_str = f"metadata LIKE '%\"filename\": \"{safe_name}\"%'"
        try:
            return self.table.search().where(filter_str).select(["text", "metadata"]).to_list()
        except Exception as e:
            logger.warning("Pack row fetch failed for %r: %s", filename, e)
            return []

    def get_pack_text_sample(self, filename: str, max_chars: int = 8000) -> str:
        """Concatenate chunk text for a pack, capped at ``max_chars``."""
        rows = self._pack_rows(filename)
        if not rows:
            return ""

        parts: list[str] = []
        total = 0
        for row in rows:
            text = (row.get("text") or "").strip()
            if not text:
                continue
            if total + len(text) > max_chars:
                parts.append(text[: max_chars - total])
                break
            parts.append(text)
            total += len(text)
        return "\n".join(parts)

    def get_pack_fingerprint(self, filename: str) -> dict:
        """Stable fingerprint for cache invalidation of auto-generated datasets."""
        rows = self._pack_rows(filename)
        chunk_count = len(rows)
        hasher = hashlib.sha256()
        for row in rows:
            hasher.update((row.get("text") or "").encode("utf-8"))
        return {"filename": filename, "chunk_count": chunk_count, "text_hash": hasher.hexdigest()}


storage = Storage()
