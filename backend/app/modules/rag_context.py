"""RAG context accumulation — multi-clause top-K merge with deduplication.

Firewall geometry still uses top-1 per clause; this module only builds the
text block injected into the upstream LLM after PASS.
"""
from __future__ import annotations

from typing import Any


def accumulate_rag_chunks(
    results: list[dict[str, Any]],
    context_chunks: list[str],
    seen_ids: set[Any],
) -> int:
    """Append unique chunk texts from search results.

    Dedup key is row ``id`` when present, otherwise the chunk ``text``.
    Preserves first-seen order (caller iterates clauses in order; within each
    clause, LanceDB nearest-first order).

    Returns the number of new chunks appended.
    """
    added = 0
    for row in results:
        key = row["id"] if "id" in row and row["id"] is not None else row.get("text")
        if key is None or key in seen_ids:
            continue
        text = row.get("text")
        if not text:
            continue
        seen_ids.add(key)
        context_chunks.append(text)
        added += 1
    return added


def join_rag_context(context_chunks: list[str]) -> str:
    """Join accumulated chunks with the standard separator."""
    return "\n---\n".join(context_chunks)
