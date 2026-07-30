"""Test LanceDB schema auto-migration in Storage module."""
import tempfile
import lancedb
import pyarrow as pa
from app.modules.storage import Storage, rabitq_schema


def test_storage_schema_migration_adds_missing_columns(monkeypatch):
    with tempfile.TemporaryDirectory() as tmp_dir:
        # 1. Manually create a legacy table missing `sparse_lexical` and RabitQ fields
        legacy_schema = pa.schema([
            pa.field("id", pa.int64()),
            pa.field("vector", pa.list_(pa.float32(), 1024)),
            pa.field("text", pa.string()),
            pa.field("metadata", pa.string()),
        ])
        db = lancedb.connect(tmp_dir)
        db.create_table("knowledge", schema=legacy_schema)

        # 2. Patch Storage.DB_PATH to point to our temporary directory
        monkeypatch.setattr("app.modules.storage.DB_PATH", tmp_dir)

        # 3. Instantiate Storage, which should trigger _ensure_schema_compatibility
        storage_instance = Storage()

        # 4. Verify all fields from rabitq_schema are present in table schema
        table_fields = storage_instance.table.schema.names
        for field in rabitq_schema.names:
            assert field in table_fields, f"Field '{field}' was not migrated to table schema"

        # 5. Verify adding a node enriched with sparse_lexical works without error
        node = {
            "id": 1,
            "vector": [0.1] * 1024,
            "text": "test content",
            "metadata": '{"filename": "test.pdf"}',
            "sparse_lexical": {123: 0.8},
        }
        storage_instance.add_nodes([node])
        assert storage_instance.count_rows() == 1
