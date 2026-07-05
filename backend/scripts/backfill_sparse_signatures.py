#!/usr/bin/env python3
"""Backfill RabitQ binary signatures and sparse_lexical for existing LanceDB rows."""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.modules.embedder import embedder
from app.modules.storage import (
    compute_rabitq_fields,
    deserialize_sparse,
    serialize_sparse,
    storage,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def _needs_backfill(row: dict) -> bool:
    missing_packed = not row.get("vector_packed")
    sparse = deserialize_sparse(row.get("sparse_lexical"))
    missing_sparse = sparse is None or len(sparse) == 0
    return missing_packed or missing_sparse


def backfill(*, dry_run: bool = False) -> tuple[int, int]:
    rows = storage.iter_all_rows()
    if not rows:
        logger.info("No rows in LanceDB — nothing to backfill.")
        return 0, 0

    updated = 0
    skipped = 0
    for row in rows:
        row_id = row.get("id")
        text = (row.get("text") or "").strip()
        if not _needs_backfill(row):
            skipped += 1
            continue

        vector = row.get("vector")
        if not vector or not text:
            logger.warning("Skipping row id=%s — missing vector or text", row_id)
            skipped += 1
            continue

        rabitq = compute_rabitq_fields(vector)
        sparse_raw = row.get("sparse_lexical")
        sparse = deserialize_sparse(sparse_raw)
        if sparse is None or len(sparse) == 0:
            output = embedder.embed_full(text)
            sparse = output.sparse

        if dry_run:
            logger.info("Would backfill id=%s sparse_keys=%d", row_id, len(sparse or {}))
            updated += 1
            continue

        sparse_json = serialize_sparse(sparse)
        storage.table.update(
            where=f"id = {int(row_id)}",
            values={
                "vector_packed": rabitq["vector_packed"],
                "centroid_distance": rabitq["centroid_distance"],
                "quantization_projection": rabitq["quantization_projection"],
                "sparse_lexical": sparse_json,
            },
        )
        updated += 1
        logger.info("Backfilled id=%s", row_id)

    return updated, skipped


def main() -> None:
    parser = argparse.ArgumentParser(description="Backfill sparse + RabitQ fields in LanceDB")
    parser.add_argument("--dry-run", action="store_true", help="Report rows without writing")
    args = parser.parse_args()
    updated, skipped = backfill(dry_run=args.dry_run)
    logger.info("Done: updated=%d skipped=%d dry_run=%s", updated, skipped, args.dry_run)


if __name__ == "__main__":
    main()
