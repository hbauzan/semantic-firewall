"""
Calibration harness — labeled dataset evaluation, threshold sweep, excitation experiment.

Isolated LanceDB (never touches production). Mirrors /chat clause segmentation.

Usage (from backend/):
    uv run python tests/calibration_suite.py evaluate --dataset calibration/datasets/automotive_v1.json
    uv run python tests/calibration_suite.py sweep --dataset calibration/datasets/automotive_v1.json
    uv run python tests/calibration_suite.py excitation-compare --dataset calibration/datasets/automotive_v1.json
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

import lancedb

from app.core.firewall import SemanticFirewall
from app.core.models import ConfigState
from app.core.recommended_thresholds import SWEEP_GRIDS, threshold_3d_grid_size
from app.modules.storage import KnowledgeNode, rabitq_schema


@dataclass
class QueryResult:
    query_id: str
    category: str
    expected: str
    actual: str
    passed: bool
    breach_reason: str | None
    failed_clause: str | None


@dataclass
class SweepPoint:
    param: str
    value: float
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def fpr(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) else 0.0

    @property
    def tpr(self) -> float:
        return self.recall

    @property
    def youden(self) -> float:
        return self.tpr - self.fpr


@dataclass
class JointSweepPoint:
    cosine_threshold: float
    excitation_threshold: int
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def fpr(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) else 0.0

    @property
    def youden(self) -> float:
        return self.recall - self.fpr


@dataclass
class TripleSweepPoint:
    cosine_threshold: float
    excitation_threshold: int
    global_noise_limit: float
    tp: int
    fp: int
    tn: int
    fn: int

    @property
    def precision(self) -> float:
        return self.tp / (self.tp + self.fp) if (self.tp + self.fp) else 0.0

    @property
    def recall(self) -> float:
        return self.tp / (self.tp + self.fn) if (self.tp + self.fn) else 0.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def fpr(self) -> float:
        return self.fp / (self.fp + self.tn) if (self.fp + self.tn) else 0.0

    @property
    def youden(self) -> float:
        return self.recall - self.fpr


def load_dataset(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def chunk_text(text: str, chunk_size: int = 400) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    for i in range(0, len(words), chunk_size // 8):
        chunk = " ".join(words[i : i + chunk_size // 8])
        if chunk.strip():
            chunks.append(chunk)
    return chunks or [text.strip()]


def ingest_pdf_to_table(pdf_path: Path, table, embedder, filename: str) -> int:
    """Embed PDF chunks into isolated LanceDB table."""
    import fitz

    from app.modules.storage import compute_rabitq_fields, serialize_sparse

    doc = fitz.open(pdf_path)
    full_text = "\n".join(page.get_text() for page in doc)
    doc.close()
    chunks = chunk_text(full_text)
    nodes = []
    for i, text in enumerate(chunks):
        output = embedder.embed_full(text)
        rabitq = compute_rabitq_fields(output.dense)
        nodes.append({
            "id": i + 1,
            "vector": output.dense,
            "sparse_lexical": serialize_sparse(output.sparse),
            "text": text,
            "metadata": json.dumps({"filename": filename, "chunk": i}),
            **rabitq,
        })
    if nodes:
        table.add(nodes)
    return len(nodes)


def _effective_excitation_threshold(
    excitation_threshold: float,
    word_count: int,
    adaptive_factor: float,
) -> float:
    if word_count < 6:
        return float(excitation_threshold) * adaptive_factor
    return float(excitation_threshold)


def measure_calibration_clause(
    clause: str,
    table,
    embedder,
    cfg_probe: ConfigState,
) -> dict:
    from app.modules.storage import deserialize_sparse

    embedding = embedder.embed_full(clause)
    cl_vec = embedding.dense
    q = np.asarray(cl_vec, dtype=np.float32)
    q_sparse = embedding.sparse
    word_count = len(clause.split())
    results = table.search(cl_vec, vector_column_name="vector").limit(cfg_probe.rag_top_k).to_list()
    if not results:
        return {
            "has_context": False,
            "entropy": float("nan"),
            "cosine_sim": 0.0,
            "activations": 0,
            "word_count": word_count,
        }

    row = results[0]
    c = np.asarray(row["vector"], dtype=np.float32).reshape(-1)
    c_sparse = deserialize_sparse(row.get("sparse_lexical"))
    if isinstance(row.get("sparse_lexical"), dict):
        c_sparse = row.get("sparse_lexical")

    eval_result = SemanticFirewall.evaluate_clause(
        q, c, cfg_probe, word_count,
        query_text=clause, q_sparse=q_sparse, c_sparse=c_sparse,
    )
    noise_trace = next((t for t in eval_result["trace"] if t["stage"] == "noise"), None)
    cosine_trace = next((t for t in eval_result["trace"] if t["stage"] == "cosine"), None)
    excitation_trace = next((t for t in eval_result["trace"] if t["stage"] == "excitation"), None)
    sparse_trace = next((t for t in eval_result["trace"] if t["stage"] == "sparse"), None)

    return {
        "has_context": True,
        "entropy": float(noise_trace["entropy"]) if noise_trace else float("nan"),
        "cosine_sim": float(cosine_trace.get("cosine_sim", cosine_trace.get("hybrid_score", 0.0))) if cosine_trace else 0.0,
        "activations": int(excitation_trace["activations"]) if excitation_trace else 0,
        "word_count": word_count,
        "sparse_sim": float(sparse_trace["sparse_sim"]) if sparse_trace else None,
    }


def measure_calibration_dataset(
    dataset: dict,
    table,
    embedder,
    cfg_probe: ConfigState,
) -> list[dict]:
    rows: list[dict] = []
    for q in dataset["queries"]:
        clauses = SemanticFirewall.segment(q["text"].strip())
        clause_rows = [
            measure_calibration_clause(cl, table, embedder, cfg_probe) for cl in clauses
        ]
        rows.append({
            "id": q["id"],
            "expected": q["expected"],
            "clauses": clause_rows,
        })
    return rows


def _clause_blocked_from_cache(clause: dict, cfg: ConfigState) -> bool:
    if not clause["has_context"]:
        return True
    if cfg.noise_enabled and clause["entropy"] < cfg.global_noise_limit:
        return True
    if cfg.cosine_enabled and clause["cosine_sim"] < cfg.cosine_threshold:
        return True
    if cfg.excitation_enabled:
        exc_th = _effective_excitation_threshold(
            cfg.excitation_threshold, clause["word_count"], cfg.adaptive_factor
        )
        if clause["activations"] < exc_th:
            return True
    return False


def _prompt_blocked_from_cache(row: dict, cfg: ConfigState) -> bool:
    return any(_clause_blocked_from_cache(cl, cfg) for cl in row["clauses"])


def confusion_from_cache(cached_rows: list[dict], cfg: ConfigState) -> tuple[int, int, int, int]:
    tp = fp = tn = fn = 0
    for row in cached_rows:
        blocked = _prompt_blocked_from_cache(row, cfg)
        true_block = row["expected"] == "block"
        if blocked and true_block:
            tp += 1
        elif blocked and not true_block:
            fp += 1
        elif not blocked and not true_block:
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def evaluate_prompt(
    prompt: str,
    cfg: ConfigState,
    table,
    embedder,
) -> tuple[bool, str | None, str | None]:
    """Return (passed, breach_reason, failed_clause). Mirrors /chat positive-mode logic."""
    from app.modules.storage import deserialize_sparse

    clauses = SemanticFirewall.segment(prompt.strip())
    negative = cfg.firewall_mode == "negative"

    for clause in clauses:
        if cfg.noise_enabled:
            entropy = SemanticFirewall.calculate_raw_entropy(clause)
            if entropy < cfg.raw_entropy_limit:
                return False, "BURST_DETECTION_BREACH", clause

        embedding = embedder.embed_full(clause)
        cl_vec = embedding.dense
        results = table.search(cl_vec, vector_column_name="vector").limit(cfg.rag_top_k).to_list()
        if not results:
            if negative:
                continue
            return False, "no_context", clause

        row = results[0]
        db_vec = row["vector"]
        q_arr = np.array(cl_vec, dtype=np.float32)
        c_arr = np.array(db_vec, dtype=np.float32)
        word_count = len(clause.split())
        c_sparse = deserialize_sparse(row.get("sparse_lexical"))
        if isinstance(row.get("sparse_lexical"), dict):
            c_sparse = row.get("sparse_lexical")

        result = SemanticFirewall.evaluate_clause(
            q_arr, c_arr, cfg, word_count,
            query_text=clause,
            q_sparse=embedding.sparse,
            c_sparse=c_sparse,
        )
        if not result["passed"]:
            return False, result["breach_reason"], clause

    return True, None, None


def verdict_to_label(passed: bool, cfg: ConfigState) -> str:
    """Map firewall pass/breach to dataset expected vocabulary."""
    if cfg.firewall_mode == "positive":
        return "pass" if passed else "block"
    return "block" if passed else "pass"


def run_evaluation(
    dataset: dict,
    cfg: ConfigState,
    table,
    embedder,
) -> list[QueryResult]:
    results: list[QueryResult] = []
    for q in dataset["queries"]:
        passed, reason, clause = evaluate_prompt(q["text"], cfg, table, embedder)
        actual = verdict_to_label(passed, cfg)
        results.append(QueryResult(
            query_id=q["id"],
            category=q["category"],
            expected=q["expected"],
            actual=actual,
            passed=actual == q["expected"],
            breach_reason=reason,
            failed_clause=clause,
        ))
    return results


def confusion(results: list[QueryResult]) -> tuple[int, int, int, int]:
    """Positive class = block (attack/off-topic). pass label = legitimate."""
    tp = fp = tn = fn = 0
    for r in results:
        pred_block = r.actual == "block"
        true_block = r.expected == "block"
        if pred_block and true_block:
            tp += 1
        elif pred_block and not true_block:
            fp += 1
        elif not pred_block and not true_block:
            tn += 1
        else:
            fn += 1
    return tp, fp, tn, fn


def setup_isolated_db(pdf_path: Path, embedder) -> tuple[object, Path]:
    test_db_path = BACKEND_DIR / "lancedb_calibration_test"
    if test_db_path.exists():
        shutil.rmtree(test_db_path)
    db = lancedb.connect(str(test_db_path))
    table = db.create_table("knowledge", schema=rabitq_schema)
    count = ingest_pdf_to_table(pdf_path, table, embedder, pdf_path.name)
    print(f"Ingested {count} chunks from {pdf_path.name}")
    return table, test_db_path


def cmd_evaluate(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset)
    dataset = load_dataset(dataset_path)
    pdf_path = BACKEND_DIR / "demo_corpus" / dataset["corpus_file"]
    if not pdf_path.exists():
        print(f"Missing corpus PDF: {pdf_path}")
        return 1

    from app.modules.embedder import Embedder

    print("Loading BGE-M3 embedder...")
    embedder = Embedder()
    table, test_db_path = setup_isolated_db(pdf_path, embedder)
    cfg = ConfigState(firewall_mode="positive")

    t0 = time.perf_counter()
    results = run_evaluation(dataset, cfg, table, embedder)
    elapsed = time.perf_counter() - t0

    tp, fp, tn, fn = confusion(results)
    accuracy = sum(1 for r in results if r.passed) / len(results)
    print(f"\nEvaluated {len(results)} queries in {elapsed:.1f}s")
    print(f"Accuracy: {accuracy:.1%}  TP={tp} FP={fp} TN={tn} FN={fn}")

    wrong = [r for r in results if not r.passed]
    if wrong:
        print("\nMismatches:")
        for r in wrong:
            print(f"  {r.query_id} [{r.category}] expected={r.expected} got={r.actual} reason={r.breach_reason}")

    report_dir = BACKEND_DIR / "calibration" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = dataset_path.stem
    out_csv = report_dir / f"{stem}_evaluate.csv"
    with out_csv.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "category", "expected", "actual", "correct", "breach_reason", "failed_clause"])
        for r in results:
            w.writerow([r.query_id, r.category, r.expected, r.actual, r.passed, r.breach_reason, r.failed_clause])
    print(f"Wrote {out_csv}")

    shutil.rmtree(test_db_path, ignore_errors=True)
    return 0 if not wrong else 2


def sweep_thresholds_3d(
    base_cfg: ConfigState,
    cached_rows: list[dict],
) -> list[TripleSweepPoint]:
    points: list[TripleSweepPoint] = []
    for cos in SWEEP_GRIDS["cosine_threshold"]:
        for exc in SWEEP_GRIDS["excitation_threshold"]:
            for noise in SWEEP_GRIDS["global_noise_limit"]:
                cfg = base_cfg.model_copy(update={
                    "cosine_threshold": cos,
                    "excitation_threshold": int(exc),
                    "global_noise_limit": noise,
                })
                tp, fp, tn, fn = confusion_from_cache(cached_rows, cfg)
                points.append(TripleSweepPoint(
                    cosine_threshold=cos,
                    excitation_threshold=int(exc),
                    global_noise_limit=noise,
                    tp=tp, fp=fp, tn=tn, fn=fn,
                ))
    return points


def _pick_triple_youden(points: list[TripleSweepPoint]) -> TripleSweepPoint:
    return max(points, key=lambda p: (p.youden, p.f1, -p.fn))


def cmd_sweep(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset)
    dataset = load_dataset(dataset_path)
    pdf_path = BACKEND_DIR / "demo_corpus" / dataset["corpus_file"]
    if not pdf_path.exists():
        print(f"Missing corpus PDF: {pdf_path}")
        return 1

    from app.modules.embedder import Embedder

    print("Loading BGE-M3 embedder...")
    embedder = Embedder()
    table, test_db_path = setup_isolated_db(pdf_path, embedder)
    base_cfg = ConfigState(firewall_mode="positive")

    report_dir = BACKEND_DIR / "calibration" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = dataset_path.stem
    out_3d = report_dir / f"{stem}_sweep_3d.csv"

    n_cos, n_exc, n_noise = threshold_3d_grid_size()
    total = n_cos * n_exc * n_noise
    print(f"3D sweep cosine×excitation×noise ({n_cos}×{n_exc}×{n_noise}={total})...")
    print("Measuring clause metrics (embed once per clause)...")
    cached_rows = measure_calibration_dataset(dataset, table, embedder, base_cfg)
    triple_points = sweep_thresholds_3d(base_cfg, cached_rows)
    winner = _pick_triple_youden(triple_points)

    with out_3d.open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "cosine_threshold", "excitation_threshold", "global_noise_limit",
            "tp", "fp", "tn", "fn", "precision", "recall", "f1", "fpr", "youden",
        ])
        for p in triple_points:
            w.writerow([
                p.cosine_threshold, p.excitation_threshold, p.global_noise_limit,
                p.tp, p.fp, p.tn, p.fn,
                f"{p.precision:.4f}", f"{p.recall:.4f}", f"{p.f1:.4f}", f"{p.fpr:.4f}", f"{p.youden:.4f}",
            ])

    print(
        f"  Youden-optimal 3D: cosine={winner.cosine_threshold} "
        f"excitation={winner.excitation_threshold} noise={winner.global_noise_limit}  "
        f"F1={winner.f1:.3f}  Youden={winner.youden:.3f}"
    )

    md_path = report_dir / f"{stem}_sweep.md"
    lines = [
        f"# Threshold sweep — {dataset['corpus_id']}",
        "",
        f"Dataset: `{dataset_path.name}`  |  Corpus: `{dataset['corpus_file']}`",
        "",
        "## Method",
        "",
        f"**3D joint sweep** — cosine × excitation × noise ({n_cos}×{n_exc}×{n_noise}={total} configs).",
        "Clause metrics cached (embed once); grid uses cached confusion only.",
        "",
        "(Negative-mode calibration deferred.)",
        "",
        "## Youden-optimal",
        "",
        "| cosine | excitation | noise | F1 | Youden |",
        "|--------|------------|-------|-----|--------|",
        f"| {winner.cosine_threshold} | {winner.excitation_threshold} | {winner.global_noise_limit} | {winner.f1:.3f} | {winner.youden:.3f} |",
        "",
        f"3D grid: `{out_3d.name}`",
    ]
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {out_3d} and {md_path}")

    shutil.rmtree(test_db_path, ignore_errors=True)
    return 0


def cmd_excitation_compare(args: argparse.Namespace) -> int:
    dataset_path = Path(args.dataset)
    dataset = load_dataset(dataset_path)
    pdf_path = BACKEND_DIR / "demo_corpus" / dataset["corpus_file"]
    if not pdf_path.exists():
        print(f"Missing corpus PDF: {pdf_path}")
        return 1

    from app.modules.embedder import Embedder

    print("Loading BGE-M3 embedder...")
    embedder = Embedder()
    table, test_db_path = setup_isolated_db(pdf_path, embedder)

    cosine_only = ConfigState(
        firewall_mode="positive",
        cosine_enabled=True,
        excitation_enabled=False,
        noise_enabled=False,
    )
    cosine_plus_exc = ConfigState(
        firewall_mode="positive",
        cosine_enabled=True,
        excitation_enabled=True,
        noise_enabled=False,
    )

    r_cos = run_evaluation(dataset, cosine_only, table, embedder)
    r_both = run_evaluation(dataset, cosine_plus_exc, table, embedder)

    # Adversarial-ish categories: off_topic, piggybacking, adversarial
    attack_cats = {"off_topic", "piggybacking", "adversarial"}
    rescued = 0
    rescued_ids: list[str] = []
    for q_cos, q_both in zip(r_cos, r_both):
        if q_cos.category not in attack_cats:
            continue
        if q_cos.actual == "pass" and q_both.actual == "block":
            rescued += 1
            rescued_ids.append(q_cos.query_id)

    print("\n=== Excitation contribution experiment ===")
    print(f"Cosine-only accuracy: {sum(1 for r in r_cos if r.passed) / len(r_cos):.1%}")
    print(f"Cosine+excitation accuracy: {sum(1 for r in r_both if r.passed) / len(r_both):.1%}")
    print(f"Adversarial/off-topic that cosine lets through but excitation blocks: {rescued}")
    if rescued_ids:
        print(f"  IDs: {', '.join(rescued_ids)}")

    report_dir = BACKEND_DIR / "calibration" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    stem = dataset_path.stem
    out_md = report_dir / f"{stem}_excitation_compare.md"
    out_md.write_text(
        "\n".join([
            f"# Excitation vs cosine — {dataset['corpus_id']}",
            "",
            f"- Cosine-only accuracy: {sum(1 for r in r_cos if r.passed) / len(r_cos):.1%}",
            f"- Cosine+excitation accuracy: {sum(1 for r in r_both if r.passed) / len(r_both):.1%}",
            f"- **Rescued by excitation** (cosine pass → both block): **{rescued}**",
            f"- Query IDs: {', '.join(rescued_ids) or 'none'}",
        ]),
        encoding="utf-8",
    )
    print(f"Wrote {out_md}")

    shutil.rmtree(test_db_path, ignore_errors=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Calibration harness for Semantic Firewall")
    sub = parser.add_subparsers(dest="command", required=True)

    p_eval = sub.add_parser("evaluate", help="Run labeled dataset against default thresholds")
    p_eval.add_argument("--dataset", required=True)

    p_sweep = sub.add_parser("sweep", help="1D threshold sweeps + Youden optimum")
    p_sweep.add_argument("--dataset", required=True)

    p_exc = sub.add_parser("excitation-compare", help="Cosine-only vs cosine+excitation")
    p_exc.add_argument("--dataset", required=True)

    args = parser.parse_args()
    if args.command == "evaluate":
        return cmd_evaluate(args)
    if args.command == "sweep":
        return cmd_sweep(args)
    if args.command == "excitation-compare":
        return cmd_excitation_compare(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
