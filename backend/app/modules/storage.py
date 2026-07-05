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

storage = Storage()
