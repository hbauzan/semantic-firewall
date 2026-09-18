"""In-process embedder determinism probe — L01 / Etapa 6 Bloque A.

Measures whether the current SentenceTransformer path emits a stable vector for
the same string, and whether PASS/BREACH is stable against a frozen demo-corpus
chunk (automotive, no network, no LanceDB).

Unit tests inject a stub callable. Live measurement:

    cd backend && uv run python tests/embedder_determinism.py --runs 100

Pytest live (skipped in ./run_tests.sh):

    cd backend && RUN_EMBEDDER_DETERMINISM=1 uv run pytest -q tests/test_embedder_determinism.py
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import platform
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

import numpy as np

from app.core.firewall import SemanticFirewall
from app.core.models import ConfigState
from app.core.settings import settings

LIVE_ENV = "RUN_EMBEDDER_DETERMINISM"
DEFAULT_N = 100
DEFAULT_ON_CORPUS = (
    "What is the recommended cold tire pressure for the rear axle on a sedan?"
)
DEFAULT_OFF_TOPIC = "What are the best mutual fund allocations for retirement planning?"
DEFAULT_REPORT = Path(__file__).resolve().parent / "embedder_determinism_report.md"
LIVE_COMMAND = "cd backend && uv run python tests/embedder_determinism.py --runs 100"
PYTEST_COMMAND = (
    f"cd backend && {LIVE_ENV}=1 uv run pytest -q tests/test_embedder_determinism.py"
)
DEMO_CORPUS_FILE = "automotive_maintenance.pdf"

EmbedFn = Callable[[str], Any]


@dataclass(frozen=True)
class VectorSpread:
    n: int
    dim: int
    unique_hashes: int
    bit_identical: bool
    max_abs_delta: float
    max_l2_delta: float


@dataclass(frozen=True)
class VerdictSpread:
    n: int
    unique_passed: tuple[bool, ...]
    unique_reasons: tuple[str | None, ...]
    flip_count: int
    stable: bool
    majority_passed: bool


@dataclass(frozen=True)
class RuntimeFingerprint:
    embedding_model: str
    sentence_transformers: str
    torch: str
    numpy: str
    python: str
    platform: str
    machine: str
    device: str
    backend_name: str


@dataclass(frozen=True)
class ProbeResult:
    prompt_role: str
    prompt: str
    expected: str | None
    vector: VectorSpread
    verdict: VerdictSpread | None


@dataclass(frozen=True)
class DeterminismReport:
    fingerprint: RuntimeFingerprint
    command: str
    pytest_command: str
    n: int
    corpus_source: str
    corpus_chunk_chars: int
    path_measured: str
    results: tuple[ProbeResult, ...]


def _pkg_version(name: str) -> str:
    try:
        return version(name)
    except PackageNotFoundError:
        return "unknown"


def collect_fingerprint(
    *,
    embedding_model: str,
    device: str,
    backend_name: str,
) -> RuntimeFingerprint:
    return RuntimeFingerprint(
        embedding_model=embedding_model,
        sentence_transformers=_pkg_version("sentence-transformers"),
        torch=_pkg_version("torch"),
        numpy=np.__version__,
        python=sys.version.split()[0],
        platform=platform.system(),
        machine=platform.machine(),
        device=device,
        backend_name=backend_name,
    )


def _as_dense(output: Any) -> np.ndarray:
    if hasattr(output, "dense"):
        return np.asarray(output.dense, dtype=np.float32).reshape(-1)
    return np.asarray(output, dtype=np.float32).reshape(-1)


def _as_sparse(output: Any) -> Mapping[int, float] | None:
    sparse = getattr(output, "sparse", None)
    if not sparse:
        return None
    return {int(k): float(v) for k, v in sparse.items()}


def collect_dense(embed_full: EmbedFn, text: str, n: int) -> list[np.ndarray]:
    if n < 1:
        raise ValueError("n must be at least 1")
    vectors: list[np.ndarray] = []
    for _ in range(n):
        vectors.append(_as_dense(embed_full(text)))
    return vectors


def collect_outputs(
    embed_full: EmbedFn, text: str, n: int
) -> list[tuple[np.ndarray, Mapping[int, float] | None]]:
    if n < 1:
        raise ValueError("n must be at least 1")
    rows: list[tuple[np.ndarray, Mapping[int, float] | None]] = []
    for _ in range(n):
        output = embed_full(text)
        rows.append((_as_dense(output), _as_sparse(output)))
    return rows


def measure_vector_spread(vectors: Sequence[np.ndarray]) -> VectorSpread:
    if not vectors:
        raise ValueError("need at least one vector")
    mats = [np.asarray(v, dtype=np.float32).reshape(-1) for v in vectors]
    dim = int(mats[0].size)
    if any(int(m.size) != dim for m in mats):
        raise ValueError("vector dimensions differ")
    ref = mats[0]
    hashes: list[str] = []
    max_abs = 0.0
    max_l2 = 0.0
    for mat in mats:
        hashes.append(hashlib.sha256(mat.tobytes()).hexdigest())
        delta = mat - ref
        max_abs = max(max_abs, float(np.max(np.abs(delta))))
        max_l2 = max(max_l2, float(np.linalg.norm(delta)))
    unique = len(set(hashes))
    return VectorSpread(
        n=len(mats),
        dim=dim,
        unique_hashes=unique,
        bit_identical=unique == 1,
        max_abs_delta=max_abs,
        max_l2_delta=max_l2,
    )


def measure_verdict_spread(
    query_vectors: Sequence[np.ndarray],
    corpus_vector: np.ndarray,
    cfg: ConfigState,
    query_text: str,
    *,
    q_sparses: Sequence[Mapping[int, float] | None] | None = None,
    c_sparse: Mapping[int, float] | None = None,
) -> VerdictSpread:
    if not query_vectors:
        raise ValueError("need at least one vector")
    corpus = np.asarray(corpus_vector, dtype=np.float32).reshape(-1)
    word_count = len(query_text.split())
    passed_list: list[bool] = []
    reasons: list[str | None] = []
    for index, query in enumerate(query_vectors):
        q_sparse = q_sparses[index] if q_sparses is not None else None
        result = SemanticFirewall.evaluate_clause(
            np.asarray(query, dtype=np.float32).reshape(-1),
            corpus,
            cfg,
            word_count=word_count,
            query_text=query_text,
            q_sparse=q_sparse,
            c_sparse=c_sparse,
        )
        passed_list.append(bool(result["passed"]))
        reasons.append(result["breach_reason"])
    unique_passed = tuple(dict.fromkeys(passed_list))
    unique_reasons = tuple(dict.fromkeys(reasons))
    flip_count = sum(left != right for left, right in zip(passed_list, passed_list[1:]))
    majority = Counter(passed_list).most_common(1)[0][0]
    return VerdictSpread(
        n=len(passed_list),
        unique_passed=unique_passed,
        unique_reasons=unique_reasons,
        flip_count=flip_count,
        stable=len(unique_passed) == 1 and len(unique_reasons) == 1,
        majority_passed=bool(majority),
    )


def load_demo_corpus_body(filename: str = DEMO_CORPUS_FILE) -> str:
    path = Path(__file__).resolve().parents[1] / "scripts" / "generate_demo_corpora.py"
    spec = importlib.util.spec_from_file_location("generate_demo_corpora", path)
    if spec is None or spec.loader is None:
        raise FileNotFoundError(f"cannot load demo corpora script: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        body = module.CORPORA[filename]
    except KeyError as exc:
        raise KeyError(f"unknown demo corpus {filename!r}") from exc
    return str(body).strip()


def first_ingest_chunk(text: str, chunk_size: int | None = None) -> str:
    size = settings.chunk_size if chunk_size is None else chunk_size
    stripped = text.strip()
    return stripped[:size]


def run_in_process_probe(
    embed_full: EmbedFn,
    *,
    n: int = DEFAULT_N,
    corpus_text: str | None = None,
    on_corpus_query: str = DEFAULT_ON_CORPUS,
    off_topic_query: str = DEFAULT_OFF_TOPIC,
    cfg: ConfigState | None = None,
    embedding_model: str | None = None,
    device: str = "unknown",
    backend_name: str = "callable",
    path_measured: str = "embed_full callable (in-process, sequential)",
) -> DeterminismReport:
    if n < 1:
        raise ValueError("n must be at least 1")
    body = corpus_text if corpus_text is not None else load_demo_corpus_body()
    chunk = first_ingest_chunk(body)
    config = cfg if cfg is not None else ConfigState()
    corpus_out = embed_full(chunk)
    corpus_dense = _as_dense(corpus_out)
    corpus_sparse = _as_sparse(corpus_out)

    on_rows = collect_outputs(embed_full, on_corpus_query, n)
    on_vectors = [row[0] for row in on_rows]
    on_sparses = [row[1] for row in on_rows]
    identity_spread = measure_vector_spread(on_vectors)
    on_verdict = measure_verdict_spread(
        on_vectors,
        corpus_dense,
        config,
        on_corpus_query,
        q_sparses=on_sparses,
        c_sparse=corpus_sparse,
    )

    off_rows = collect_outputs(embed_full, off_topic_query, n)
    off_vectors = [row[0] for row in off_rows]
    off_sparses = [row[1] for row in off_rows]
    off_spread = measure_vector_spread(off_vectors)
    off_verdict = measure_verdict_spread(
        off_vectors,
        corpus_dense,
        config,
        off_topic_query,
        q_sparses=off_sparses,
        c_sparse=corpus_sparse,
    )

    fingerprint = collect_fingerprint(
        embedding_model=embedding_model or settings.embedding_model,
        device=device,
        backend_name=backend_name,
    )
    return DeterminismReport(
        fingerprint=fingerprint,
        command=LIVE_COMMAND,
        pytest_command=PYTEST_COMMAND,
        n=n,
        corpus_source=f"generate_demo_corpora.CORPORA[{DEMO_CORPUS_FILE!r}] first ingest chunk",
        corpus_chunk_chars=len(chunk),
        path_measured=path_measured,
        results=(
            ProbeResult(
                prompt_role="identity",
                prompt=on_corpus_query,
                expected=None,
                vector=identity_spread,
                verdict=None,
            ),
            ProbeResult(
                prompt_role="on_corpus",
                prompt=on_corpus_query,
                expected="pass",
                vector=identity_spread,
                verdict=on_verdict,
            ),
            ProbeResult(
                prompt_role="off_topic",
                prompt=off_topic_query,
                expected="block",
                vector=off_spread,
                verdict=off_verdict,
            ),
        ),
    )


def render_markdown(report: DeterminismReport) -> str:
    fp = report.fingerprint
    lines = [
        "# Embedder determinism — L01",
        "",
        "Baseline for L05 (TEI vs SentenceTransformer) and Etapa 6 Bloque A.",
        "Jitter is recorded, not treated as a CI failure. Cross-host bit-exactness is not claimed.",
        "",
        "## Command",
        "",
        f"`{report.command}`",
        "",
        f"Pytest live: `{report.pytest_command}`",
        "",
        "## Runtime fingerprint",
        "",
        f"- embedding_model: `{fp.embedding_model}`",
        f"- sentence-transformers: `{fp.sentence_transformers}`",
        f"- torch: `{fp.torch}`",
        f"- numpy: `{fp.numpy}`",
        f"- python: `{fp.python}`",
        f"- platform: `{fp.platform}` `{fp.machine}`",
        f"- device: `{fp.device}`",
        f"- backend_name: `{fp.backend_name}`",
        f"- path_measured: {report.path_measured}",
        f"- N: {report.n}",
        f"- corpus_source: {report.corpus_source} ({report.corpus_chunk_chars} chars)",
        "",
        "## Vector spread",
        "",
        "| role | prompt (truncated) | n | dim | unique_hashes | bit_identical | max_abs_delta | max_l2_delta |",
        "| :--- | :--- | ---: | ---: | ---: | :---: | ---: | ---: |",
    ]
    for item in report.results:
        if item.prompt_role == "on_corpus":
            continue
        prompt = item.prompt if len(item.prompt) <= 72 else item.prompt[:69] + "..."
        spread = item.vector
        lines.append(
            f"| {item.prompt_role} | {prompt} | {spread.n} | {spread.dim} | "
            f"{spread.unique_hashes} | {str(spread.bit_identical).lower()} | "
            f"{spread.max_abs_delta:.8g} | {spread.max_l2_delta:.8g} |"
        )
    lines.extend(
        [
            "",
            "## PASS/BREACH spread (frozen automotive chunk, production ConfigState unless noted)",
            "",
            "| role | expected | n | stable | flip_count | majority_passed | unique_passed | unique_reasons |",
            "| :--- | :--- | ---: | :---: | ---: | :---: | :--- | :--- |",
        ]
    )
    for item in report.results:
        if item.verdict is None:
            continue
        verdict = item.verdict
        lines.append(
            f"| {item.prompt_role} | {item.expected} | {verdict.n} | "
            f"{str(verdict.stable).lower()} | {verdict.flip_count} | "
            f"{str(verdict.majority_passed).lower()} | {list(verdict.unique_passed)!s} | "
            f"{list(verdict.unique_reasons)!s} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Sequential in-process calls only. A second process with a different OpenMP seed is a different runtime.",
            "- `app.modules.embedder.embedder` and `UnifiedInferenceDispatcher` each construct a SentenceTransformer. L01 measures the singleton `embed_full` path.",
            "- Identity probe reuses the on-corpus query embeddings (same string, N times). Off-topic is a second N loop against the same frozen corpus vector.",
            "- Raw 1024-D vectors are not stored in this report.",
            "",
            "## Interpretation",
            "",
        ]
    )
    identity = next(item for item in report.results if item.prompt_role == "identity")
    on_corpus = next(item for item in report.results if item.prompt_role == "on_corpus")
    off_topic = next(item for item in report.results if item.prompt_role == "off_topic")
    if identity.vector.bit_identical:
        lines.append(
            f"- Dense vectors are **bit-identical** on this fingerprint "
            f"(N={identity.vector.n}, dim={identity.vector.dim}, max_abs_delta=0, max_l2_delta=0)."
        )
    else:
        lines.append(
            f"- Dense vectors **jitter** on this fingerprint: "
            f"unique_hashes={identity.vector.unique_hashes}, "
            f"max_abs_delta={identity.vector.max_abs_delta:.8g}, "
            f"max_l2_delta={identity.vector.max_l2_delta:.8g}."
        )
    if on_corpus.verdict is not None:
        lines.append(
            f"- On-corpus PASS/BREACH is "
            f"{'stable' if on_corpus.verdict.stable else 'UNSTABLE'} "
            f"(flip_count={on_corpus.verdict.flip_count}, "
            f"majority_passed={on_corpus.verdict.majority_passed}, "
            f"reasons={list(on_corpus.verdict.unique_reasons)}). "
            "A stable BREACH here is a calibration/geometry fact, not float jitter."
        )
    if off_topic.verdict is not None:
        lines.append(
            f"- Off-topic PASS/BREACH is "
            f"{'stable' if off_topic.verdict.stable else 'UNSTABLE'} "
            f"(flip_count={off_topic.verdict.flip_count}, "
            f"majority_passed={off_topic.verdict.majority_passed}, "
            f"reasons={list(off_topic.verdict.unique_reasons)})."
        )
    lines.append(
        "- Cross-hardware bit-exactness (another Mac, NVIDIA, CPU-only) is **not** claimed."
    )
    lines.append("")
    return "\n".join(lines)


def write_report(report: DeterminismReport, path: Path | None = None) -> Path:
    target = path if path is not None else DEFAULT_REPORT
    target.write_text(render_markdown(report), encoding="utf-8")
    return target


def run_live_probe(n: int = DEFAULT_N) -> DeterminismReport:
    from app.modules.embedder import embedder

    backend = getattr(embedder, "_backend", None)
    backend_name = getattr(backend, "backend_name", "unknown")
    device = getattr(embedder, "device", "unknown")
    return run_in_process_probe(
        embedder.embed_full,
        n=n,
        embedding_model=settings.embedding_model,
        device=str(device),
        backend_name=str(backend_name),
        path_measured=(
            "app.modules.embedder.embedder.embed_full "
            "(singleton, sequential; dispatcher holds a second ST instance)"
        ),
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="L01 in-process embedder determinism probe")
    parser.add_argument("--runs", type=int, default=DEFAULT_N)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args(argv)
    try:
        report = run_live_probe(n=args.runs)
    except Exception as exc:  # noqa: BLE001 — CLI must fail closed if it cannot embed
        print(f"L01 probe failed before completing N={args.runs}: {exc}", file=sys.stderr)
        return 1
    path = write_report(report, args.report)
    print(render_markdown(report))
    print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
