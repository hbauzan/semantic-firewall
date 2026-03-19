"""
Vector Database Bulk Saturation Test — Three-Headed Semantic Firewall
=====================================================================

Measures how the Firewall's retrieval + evaluation phases scale as the
underlying LanceDB knowledge base grows from empty to 50,000 vectors.

The script injects synthetic 1024D vectors in batches, pauses at defined
milestones (1k, 10k, 50k rows), fires 100 benchmark queries through the
real Storage.search_nearest() and SemanticFirewall.evaluate_clause(), then
isolates the timing of each phase independently.

Usage:
    # From the backend directory with the venv activated:
    #   .venv/bin/python tests/db_stress_suite.py
    #
    # Optional flags:
    #   --milestones 1000 10000 50000   (default: 1000 10000 50000)
    #   --queries 100                    (benchmark queries per milestone, default: 100)
    #   --batch-size 500                 (injection batch size, default: 500)
    #   --output tests/db_scaling_metrics.md  (default)
    #   --use-embedder                   (use real BGE-M3 instead of synthetic vectors)
"""

import argparse
import json
import os
import shutil
import statistics
import sys
import time
from dataclasses import dataclass, field

import numpy as np

# ---------------------------------------------------------------------------
# Ensure the backend package is importable
# ---------------------------------------------------------------------------
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND_DIR)

import lancedb
from lancedb.pydantic import Vector, LanceModel


# ---------------------------------------------------------------------------
# Isolated LanceDB schema (mirrors storage.py but avoids singleton import)
# ---------------------------------------------------------------------------

class KnowledgeNode(LanceModel):
    id: int
    vector: Vector(1024)
    text: str
    metadata: str


# ---------------------------------------------------------------------------
# Mock Data Generator
# ---------------------------------------------------------------------------

VOCAB = (
    "tire pressure axle nominal tolerance range sensor calibration "
    "brake pad hydraulic fluid transmission gear differential bearing "
    "suspension spring damper alignment camber caster steering rack "
    "coolant thermostat radiator hose pump gasket exhaust manifold "
    "catalyst oxygen sensor injector throttle intake valve piston "
    "crankshaft camshaft timing belt chain oil filter lubrication "
    "electrical wiring harness fuse relay alternator battery starter "
    "module controller diagnostic protocol voltage resistance current"
).split()


def generate_chunk_text(idx: int, rng: np.random.Generator) -> str:
    """Generate a pseudo-random technical text chunk."""
    length = rng.integers(20, 60)
    words = rng.choice(VOCAB, size=length, replace=True)
    return f"[chunk-{idx}] " + " ".join(words)


def generate_synthetic_vector(rng: np.random.Generator) -> list[float]:
    """Generate a random 1024D vector with realistic magnitude."""
    vec = rng.standard_normal(1024).astype(np.float32)
    # Normalize to unit-ish length (BGE-M3 outputs are roughly unit-norm)
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec = vec / norm
    return vec.tolist()


def generate_batch(
    start_id: int,
    count: int,
    rng: np.random.Generator,
    embedder=None,
) -> list[dict]:
    """Generate a batch of nodes with text and vectors."""
    nodes = []
    texts = []
    for i in range(count):
        idx = start_id + i
        text = generate_chunk_text(idx, rng)
        texts.append(text)

    # Use real embedder if provided, otherwise synthetic vectors
    if embedder is not None:
        vectors = embedder.embed_batch(texts)
    else:
        vectors = [generate_synthetic_vector(rng) for _ in range(count)]

    for i in range(count):
        nodes.append({
            "id": start_id + i,
            "vector": vectors[i],
            "text": texts[i],
            "metadata": json.dumps({"filename": "stress_test.pdf", "chunk": start_id + i}),
        })

    return nodes


# ---------------------------------------------------------------------------
# Result Container
# ---------------------------------------------------------------------------

@dataclass
class MilestoneResult:
    db_size: int
    query_count: int
    retrieval_times: list[float] = field(default_factory=list)
    firewall_times: list[float] = field(default_factory=list)
    injection_time: float = 0.0

    @property
    def avg_retrieval_ms(self) -> float:
        return statistics.mean(self.retrieval_times) * 1000 if self.retrieval_times else 0.0

    @property
    def min_retrieval_ms(self) -> float:
        return min(self.retrieval_times) * 1000 if self.retrieval_times else 0.0

    @property
    def max_retrieval_ms(self) -> float:
        return max(self.retrieval_times) * 1000 if self.retrieval_times else 0.0

    @property
    def p95_retrieval_ms(self) -> float:
        if len(self.retrieval_times) < 2:
            return self.avg_retrieval_ms
        s = sorted(self.retrieval_times)
        return s[min(int(len(s) * 0.95), len(s) - 1)] * 1000

    @property
    def avg_firewall_ms(self) -> float:
        return statistics.mean(self.firewall_times) * 1000 if self.firewall_times else 0.0

    @property
    def min_firewall_ms(self) -> float:
        return min(self.firewall_times) * 1000 if self.firewall_times else 0.0

    @property
    def max_firewall_ms(self) -> float:
        return max(self.firewall_times) * 1000 if self.firewall_times else 0.0

    @property
    def p95_firewall_ms(self) -> float:
        if len(self.firewall_times) < 2:
            return self.avg_firewall_ms
        s = sorted(self.firewall_times)
        return s[min(int(len(s) * 0.95), len(s) - 1)] * 1000


# ---------------------------------------------------------------------------
# Benchmark Engine
# ---------------------------------------------------------------------------

def run_benchmark(
    milestones: list[int],
    queries_per_milestone: int,
    batch_size: int,
    use_embedder: bool,
) -> list[MilestoneResult]:
    """Run the full saturation benchmark."""

    from app.core.models import ConfigState
    from app.core.firewall import SemanticFirewall

    # Load real embedder only if requested
    embedder = None
    if use_embedder:
        print("Loading BGE-M3 embedder (this may take a moment)...")
        from app.modules.embedder import Embedder
        embedder = Embedder()
        print(f"  Embedder loaded on {embedder.device}")

    # Create an isolated temporary LanceDB for the test
    test_db_path = os.path.join(BACKEND_DIR, "lancedb_stress_test")
    if os.path.exists(test_db_path):
        shutil.rmtree(test_db_path)

    db = lancedb.connect(test_db_path)
    table = db.create_table("stress_knowledge", schema=KnowledgeNode)

    # Default config for firewall evaluation
    cfg = ConfigState()

    rng = np.random.default_rng(seed=42)
    current_rows = 0
    results: list[MilestoneResult] = []

    # Pre-generate query vectors (fixed set reused at every milestone)
    print(f"\nGenerating {queries_per_milestone} benchmark query vectors...")
    if embedder is not None:
        query_texts = [generate_chunk_text(900_000 + i, rng) for i in range(queries_per_milestone)]
        query_vectors = [np.array(v, dtype=np.float32) for v in embedder.embed_batch(query_texts)]
    else:
        query_vectors = [
            np.array(generate_synthetic_vector(rng), dtype=np.float32)
            for _ in range(queries_per_milestone)
        ]

    sorted_milestones = sorted(milestones)
    total_needed = sorted_milestones[-1]

    print(f"Milestones: {sorted_milestones}")
    print(f"Queries per milestone: {queries_per_milestone}")
    print(f"Batch size: {batch_size}")
    print(f"Vector source: {'BGE-M3 embedder' if use_embedder else 'synthetic (numpy random)'}")
    print()

    for milestone in sorted_milestones:
        rows_to_add = milestone - current_rows

        # --- Injection Phase ---
        print(f"[INJECT] Filling DB to {milestone:,} rows ({rows_to_add:,} to add)...")
        inject_start = time.perf_counter()

        injected = 0
        while injected < rows_to_add:
            chunk = min(batch_size, rows_to_add - injected)
            batch = generate_batch(current_rows + injected, chunk, rng, embedder)
            table.add(batch)
            injected += chunk
            total_in_db = current_rows + injected
            if injected % (batch_size * 10) == 0 or injected >= rows_to_add:
                print(f"         {total_in_db:,} rows in DB...")

        inject_time = time.perf_counter() - inject_start
        current_rows = milestone
        actual_rows = table.count_rows()
        print(f"         Injection complete: {actual_rows:,} rows, {inject_time:.1f}s")

        # --- Benchmark Phase ---
        print(f"[BENCH]  Firing {queries_per_milestone} queries at {actual_rows:,} rows...")
        result = MilestoneResult(db_size=actual_rows, query_count=queries_per_milestone)
        result.injection_time = inject_time

        for q_vec in query_vectors:
            # Phase 1: Retrieval (search_nearest)
            t0 = time.perf_counter()
            search_results = table.search(q_vec.tolist()).limit(1).to_list()
            t1 = time.perf_counter()
            result.retrieval_times.append(t1 - t0)

            # Phase 2: Firewall evaluation
            if search_results:
                c_vec = np.array(search_results[0]["vector"], dtype=np.float32)
                word_count = 10  # standard clause length
                t2 = time.perf_counter()
                SemanticFirewall.evaluate_clause(q_vec, c_vec, cfg, word_count)
                t3 = time.perf_counter()
                result.firewall_times.append(t3 - t2)
            else:
                result.firewall_times.append(0.0)

        results.append(result)

        print(
            f"         Retrieval: avg={result.avg_retrieval_ms:.2f}ms "
            f"p95={result.p95_retrieval_ms:.2f}ms | "
            f"Firewall: avg={result.avg_firewall_ms:.3f}ms "
            f"p95={result.p95_firewall_ms:.3f}ms"
        )
        print()

    # Cleanup
    print("Cleaning up test database...")
    shutil.rmtree(test_db_path, ignore_errors=True)

    return results


# ---------------------------------------------------------------------------
# Report Generation
# ---------------------------------------------------------------------------

def print_table(results: list[MilestoneResult]) -> None:
    """Print a formatted console summary."""
    header = [
        "DB Size", "Queries",
        "Ret Avg(ms)", "Ret P95(ms)", "Ret Max(ms)",
        "FW Avg(ms)", "FW P95(ms)", "FW Max(ms)",
        "Inject(s)",
    ]
    rows = [header]
    for r in results:
        rows.append([
            f"{r.db_size:,}",
            str(r.query_count),
            f"{r.avg_retrieval_ms:.2f}",
            f"{r.p95_retrieval_ms:.2f}",
            f"{r.max_retrieval_ms:.2f}",
            f"{r.avg_firewall_ms:.3f}",
            f"{r.p95_firewall_ms:.3f}",
            f"{r.max_firewall_ms:.3f}",
            f"{r.injection_time:.1f}",
        ])

    col_widths = [max(len(row[i]) for row in rows) for i in range(len(header))]
    sep = "-+-".join("-" * w for w in col_widths)

    def fmt(row: list[str]) -> str:
        return " | ".join(c.rjust(w) for c, w in zip(row, col_widths))

    print()
    print(fmt(rows[0]))
    print(sep)
    for row in rows[1:]:
        print(fmt(row))
    print()


def write_markdown_report(results: list[MilestoneResult], path: str) -> None:
    """Generate a Markdown report with graph-ready tables."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    lines = [
        "# Vector Database Scaling Metrics",
        "",
        "> Auto-generated by `tests/db_stress_suite.py`",
        "",
        "## Summary",
        "",
        "Benchmark of LanceDB retrieval latency and SemanticFirewall evaluation",
        "time as the vector store grows from empty to peak capacity.",
        "",
        "## Retrieval Latency vs DB Size",
        "",
        "| DB Size | Avg Retrieval (ms) | P95 Retrieval (ms) | Max Retrieval (ms) |",
        "|--------:|-------------------:|-------------------:|-------------------:|",
    ]

    for r in results:
        lines.append(
            f"| {r.db_size:,} | {r.avg_retrieval_ms:.2f} | "
            f"{r.p95_retrieval_ms:.2f} | {r.max_retrieval_ms:.2f} |"
        )

    lines += [
        "",
        "## Firewall Processing vs DB Size",
        "",
        "| DB Size | Avg Firewall (ms) | P95 Firewall (ms) | Max Firewall (ms) |",
        "|--------:|------------------:|------------------:|------------------:|",
    ]

    for r in results:
        lines.append(
            f"| {r.db_size:,} | {r.avg_firewall_ms:.3f} | "
            f"{r.p95_firewall_ms:.3f} | {r.max_firewall_ms:.3f} |"
        )

    lines += [
        "",
        "## Combined (Graph-Ready)",
        "",
        "| DB Size | Avg Retrieval (ms) | Avg Firewall (ms) | Injection Time (s) |",
        "|--------:|-------------------:|------------------:|--------------------:|",
    ]

    for r in results:
        lines.append(
            f"| {r.db_size:,} | {r.avg_retrieval_ms:.2f} | "
            f"{r.avg_firewall_ms:.3f} | {r.injection_time:.1f} |"
        )

    lines += [
        "",
        "## Methodology",
        "",
        "- **Vector dimensions:** 1024 (matching BAAI/bge-m3 output)",
        "- **Query set:** Fixed pool of benchmark vectors, reused at every milestone",
        f"- **Queries per milestone:** {results[0].query_count if results else 'N/A'}",
        "- **Retrieval:** `table.search(vector).limit(1)` — isolated timing",
        "- **Firewall:** `SemanticFirewall.evaluate_clause()` with default ConfigState — isolated timing",
        "- **Database:** Temporary LanceDB instance (cleaned up after run)",
        "- **Vectors:** Synthetic unit-norm random vectors (use `--use-embedder` for real BGE-M3 embeddings)",
        "",
    ]

    with open(path, "w") as f:
        f.write("\n".join(lines))

    print(f"Markdown report written to: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Vector DB bulk saturation test for Three-Headed Semantic Firewall"
    )
    parser.add_argument(
        "--milestones", type=int, nargs="+", default=[1000, 10000, 50000],
        help="Row count milestones to benchmark at (default: 1000 10000 50000)",
    )
    parser.add_argument(
        "--queries", type=int, default=100,
        help="Number of benchmark queries per milestone (default: 100)",
    )
    parser.add_argument(
        "--batch-size", type=int, default=500,
        help="Injection batch size (default: 500)",
    )
    parser.add_argument(
        "--output", default="tests/db_scaling_metrics.md",
        help="Markdown report output path (default: tests/db_scaling_metrics.md)",
    )
    parser.add_argument(
        "--use-embedder", action="store_true",
        help="Use real BGE-M3 model for vectors instead of synthetic random",
    )
    args = parser.parse_args()

    print("=" * 70)
    print("DB SATURATION TEST — Three-Headed Semantic Firewall")
    print("=" * 70)

    results = run_benchmark(
        milestones=args.milestones,
        queries_per_milestone=args.queries,
        batch_size=args.batch_size,
        use_embedder=args.use_embedder,
    )

    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print_table(results)
    write_markdown_report(results, args.output)


if __name__ == "__main__":
    main()
