import lancedb
from lancedb.pydantic import Vector, LanceModel
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "lancedb_data")

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
        if self.table_name not in self.db.table_names():
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
        
        # We can just fetch all ids and max, or keep track.
        # Since LanceDB doesn't have a direct max, we'll order by id desc
        res = self.table.search().limit(1).select(["id"]).to_list()
        # Note: search without vector does a vector-less scan but LanceDB doesn't sort by non-vector fields easily in search
        # Instead, we can read the lance dataset.
        ds = self.table.to_lance()
        if ds.count_rows() == 0:
            return 0
        import pyarrow.compute as pc
        return pc.max(ds.to_table()["id"]).as_py()
        
    def search_nearest(self, query_vector: list[float], k: int = 1):
        if self.table.count_rows() == 0:
            return []
        
        results = self.table.search(query_vector).limit(k).to_list()
        return results

    def count_rows(self) -> int:
        return self.table.count_rows()

    def get_summary(self) -> list[dict]:
        if self.table.count_rows() == 0:
            return []
        
        # LanceDB doesn't natively group_by text extracted from metadata.
        # We will load the dataset and aggregate manually for the HUD.
        ds = self.table.to_lance()
        if ds.count_rows() == 0:
            return []
            
        import json
        metadata_col = ds.to_table()["metadata"].to_pylist()
        
        packs = {}
        for m_str in metadata_col:
            try:
                m = json.loads(m_str)
                fname = m.get("filename", "unknown")
                packs[fname] = packs.get(fname, 0) + 1
            except:
                pass
                
        return [{"filename": k, "chunks": v} for k, v in packs.items()]

    def delete_pack(self, filename: str):
        if self.table.count_rows() == 0:
            return
            
        # LanceDB SQL filter using LIKE on the metadata string
        # metadata contains {"filename": "..."}
        # A simple string match works for our purposes.
        filter_str = f"metadata LIKE '%\"filename\": \"{filename}\"%'"
        self.table.delete(filter_str)

storage = Storage()
