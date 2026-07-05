import hashlib
import json
import lancedb
from lancedb.pydantic import Vector, LanceModel
import logging
import os
import re

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "lancedb_data")

# Whitelist: only allow safe characters in filenames used in queries
_SAFE_FILENAME_RE = re.compile(r'^[\w\s.\-()]+$', re.UNICODE)

class KnowledgeNode(LanceModel):
    id: int
    vector: Vector(1024)
    text: str
    metadata: str # json string

class Storage:
    def __init__(self):
        self.db = lancedb.connect(DB_PATH)
        self.table_name = "knowledge"
        
        # Initialize table if not exists
        existing = self.db.list_tables()
        table_list = existing.tables if hasattr(existing, 'tables') else list(existing)
        if self.table_name not in table_list:
            self.table = self.db.create_table(self.table_name, schema=KnowledgeNode)
        else:
            self.table = self.db.open_table(self.table_name)

    def add_nodes(self, nodes: list[dict]):
        """
        nodes should be a list of dicts:
        {"id": int, "vector": list[float], "text": str, "metadata": str}
        """
        if nodes:
            self.table.add(nodes)

    def get_max_id(self) -> int:
        if self.table.count_rows() == 0:
            return 0
        rows = self.table.search().select(["id"]).to_list()
        return max(row["id"] for row in rows)
        
    def search_nearest(self, query_vector: list[float], k: int = 1):
        if self.table.count_rows() == 0:
            return []
        
        results = self.table.search(query_vector).limit(k).to_list()
        return results

    def resolve_active_pack(self, active_corpus_file: str | None = None) -> str | None:
        """Resolve which pack scopes firewall/RAG search.

        Priority: explicit active_corpus_file (if loaded) → sole loaded pack → None (global).
        """
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
        """Pack-scoped nearest-neighbor search when a pack is active; else global."""
        pack = self.resolve_active_pack(active_corpus_file)
        if pack:
            return self.search_nearest_for_pack(query_vector, pack, k=k)
        return self.search_nearest(query_vector, k=k)

    def search_nearest_for_pack(self, query_vector: list[float], filename: str, k: int = 1):
        """Nearest-neighbor search limited to vectors from a single pack."""
        if self.table.count_rows() == 0:
            return []

        if not filename or not _SAFE_FILENAME_RE.match(filename):
            logger.warning("Rejected unsafe filename for pack search: %r", filename)
            return []

        safe_name = filename.replace("'", "''")
        filter_str = f"metadata LIKE '%\"filename\": \"{safe_name}\"%'"
        try:
            return self.table.search(query_vector).where(filter_str).limit(k).to_list()
        except Exception as e:
            logger.warning("Pack-scoped search failed, falling back to global: %s", e)
            return self.search_nearest(query_vector, k=k)

    def count_rows(self) -> int:
        return self.table.count_rows()

    def get_summary(self) -> list[dict]:
        if self.table.count_rows() == 0:
            return []

        import json
        # Use LanceDB query builder — no extra dependencies required.
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

        # Validate filename to prevent SQL injection via LIKE filter
        if not filename or not _SAFE_FILENAME_RE.match(filename):
            logger.warning("Rejected unsafe filename for deletion: %r", filename)
            raise ValueError(f"Invalid filename: contains disallowed characters")

        # Escape single quotes for the SQL LIKE clause
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
