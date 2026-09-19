"""Prisma envelope probe. Lab only. Does not touch evaluate_clause.

  cd backend && uv run python -m calibration.dimension_probe.run --budget-sec 2700
"""

from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path

import numpy as np

from calibration.dimension_probe.generate import (
    DEFAULT_SIBLING_LANCEDB,
    build_probe_rows,
    default_prisma_json,
    export_prisma_chunks,
    load_prisma_chunks,
)
from calibration.dimension_probe.columns import pair_matrix, theme_groups
from calibration.dimension_probe.lomo import split_oficio
from calibration.dimension_probe.metrics import (
    centroid,
    centroid_abs_delta,
    cosine,
    dim_spans,
    envelope_bounds,
    fraction_dims_inside,
    intra_mean_cosine,
    mean_abs_zscore,
    pairwise_mean_cosine,
    relative_slack,
    rows_inside_almost,
    rows_inside_strict,
    same_sign_dim_count,
    span_compare,
    top_moving_dims,
)

PAIRS: tuple[tuple[str, str, str], ...] = (
    ("prisma_chunk", "on_corpus", "prisma vs on_corpus"),
    ("prisma_chunk", "deviation", "prisma vs deviation"),
    ("prisma_chunk", "disguise", "prisma vs disguise"),
    ("prisma_chunk", "piggy_full", "prisma vs piggy_full"),
    ("prisma_chunk", "piggy_clause_torta", "prisma vs piggy_torta"),
    ("prisma_chunk", "names_chunk", "prisma vs nombres"),
    ("prisma_chunk", "it_chunk", "prisma vs IT"),
    ("prisma_chunk", "poetry", "prisma vs poesia"),
    ("prisma_oficio", "on_corpus", "oficio vs on_corpus"),
    ("prisma_oficio", "piggy_full", "oficio vs piggy_full"),
    ("prisma_oficio", "piggy_clause_torta", "oficio vs piggy_torta"),
    ("prisma_oficio", "names_chunk", "oficio vs nombres"),
    ("prisma_chunk", "prisma_oficio", "libro vs oficio"),
    ("on_corpus", "deviation", "on_corpus vs deviation"),
    ("disguise", "poetry", "disguise vs poesia"),
)


def _out_dir() -> Path:
    return Path(__file__).resolve().parent / "out"


def _embed_groups(
    rows: list[tuple[str, str]],
    embed_batch,
    batch_size: int,
    deadline: float,
) -> dict[str, np.ndarray]:
    buckets: dict[str, list[list[float]]] = defaultdict(list)
    done = 0
    t0 = time.perf_counter()
    for start in range(0, len(rows), batch_size):
        if time.perf_counter() > deadline:
            break
        chunk = rows[start : start + batch_size]
        texts = [text for _g, text in chunk]
        vecs = embed_batch(texts)
        for (group, _text), vec in zip(chunk, vecs, strict=True):
            buckets[group].append(vec)
        done += len(chunk)
        elapsed = time.perf_counter() - t0
        rate = done / max(elapsed, 1e-6)
        print(
            f"embedded {done}/{len(rows)}  {rate:.1f} texts/s  {elapsed:.0f}s elapsed",
            flush=True,
        )
    return {k: np.asarray(v, dtype=np.float32) for k, v in buckets.items() if v}


def _pair_report(groups: dict[str, np.ndarray]) -> list[dict]:
    report = []
    for left, right, label in PAIRS:
        if left not in groups or right not in groups:
            continue
        a, b = groups[left], groups[right]
        delta = centroid_abs_delta(a, b)
        report.append(
            {
                "pair": label,
                "left": left,
                "right": right,
                "n_left": int(a.shape[0]),
                "n_right": int(b.shape[0]),
                "centroid_cosine": round(cosine(centroid(a), centroid(b)), 4),
                "pairwise_cosine": round(pairwise_mean_cosine(a, b), 4),
                "median_abs_delta": round(float(np.median(delta)), 5),
                "p95_abs_delta": round(float(np.quantile(delta, 0.95)), 5),
                "top20": [{"dim": i, "delta": round(v, 5)} for i, v in top_moving_dims(delta, 20)],
            }
        )
    return report


def _envelope_report(groups: dict[str, np.ndarray], paint_key: str = "prisma_chunk") -> dict:
    if paint_key not in groups:
        raise RuntimeError(f"{paint_key} missing after embed — abort, no molds.")
    prisma = groups[paint_key]
    lo, hi = envelope_bounds(prisma)
    spans = dim_spans(prisma)
    mean = np.mean(prisma, axis=0)
    std = np.std(prisma, axis=0)
    families = {}
    for name, mat in sorted(groups.items()):
        slack1 = relative_slack(spans, 1.0)
        slack5 = relative_slack(spans, 5.0)
        frac1 = fraction_dims_inside(mat, lo, hi, slack1)
        frac5 = fraction_dims_inside(mat, lo, hi, slack5)
        families[name] = {
            "n": int(mat.shape[0]),
            "intra_cosine": round(intra_mean_cosine(mat), 4),
            "mean_frac_dims_inside_1pct": round(float(np.mean(frac1)), 4),
            "mean_frac_dims_inside_5pct": round(float(np.mean(frac5)), 4),
            "rows_inside_strict_5pct": round(rows_inside_strict(mat, lo, hi, slack5), 4),
            "rows_inside_95dims_5pct": round(rows_inside_almost(mat, lo, hi, slack5, 0.95), 4),
            "mean_abs_zscore": round(mean_abs_zscore(mat, mean, std), 4),
            "same_sign_dims": same_sign_dim_count(mat),
        }
    return {
        "paint": paint_key,
        "prisma_n": int(prisma.shape[0]),
        "median_span": round(float(np.median(spans)), 5),
        "p95_span": round(float(np.quantile(spans, 0.95)), 5),
        "families": families,
    }


def _compare_envelopes(raw: dict, oficio: dict) -> dict:
    fams: dict[str, dict] = {}
    for name in sorted(set(raw["families"]) | set(oficio["families"])):
        a = raw["families"].get(name)
        b = oficio["families"].get(name)
        if a is None or b is None:
            continue
        fams[name] = {
            "strict_5pct_raw": a["rows_inside_strict_5pct"],
            "strict_5pct_oficio": b["rows_inside_strict_5pct"],
            "strict_5pct_delta": round(
                b["rows_inside_strict_5pct"] - a["rows_inside_strict_5pct"], 4
            ),
            "z_raw": a["mean_abs_zscore"],
            "z_oficio": b["mean_abs_zscore"],
            "z_delta": round(b["mean_abs_zscore"] - a["mean_abs_zscore"], 4),
        }
    return {
        "median_span_raw": raw["median_span"],
        "median_span_oficio": oficio["median_span"],
        "p95_span_raw": raw["p95_span"],
        "p95_span_oficio": oficio["p95_span"],
        "families": fams,
    }


def _paint_groups(
    groups: dict[str, np.ndarray],
    keep_indices: tuple[int, ...],
) -> dict[str, np.ndarray]:
    """Same embeddings. Oficio / lomo are slices of prisma_chunk row order."""
    prisma = groups["prisma_chunk"]
    n = int(prisma.shape[0])
    keep = np.asarray([i for i in keep_indices if 0 <= i < n], dtype=np.intp)
    if keep.size == 0:
        raise RuntimeError("oficio split kept 0 chunks — abort.")
    mask = np.zeros(n, dtype=bool)
    mask[keep] = True
    out = dict(groups)
    out["prisma_oficio"] = prisma[mask]
    if int((~mask).sum()) > 0:
        out["prisma_lomo"] = prisma[~mask]
    return out


def _hypothesis(pairs: list[dict], envelope: dict) -> dict[str, bool | None]:
    by = {p["pair"]: p["centroid_cosine"] for p in pairs}
    fam = envelope["families"]

    def _inside(name: str, key: str = "mean_frac_dims_inside_5pct") -> float | None:
        row = fam.get(name)
        return None if row is None else float(row[key])

    def _gt_inside(a: str, b: str) -> bool | None:
        va, vb = _inside(a), _inside(b)
        if va is None or vb is None:
            return None
        return va > vb

    def _gt_cos(a: str, b: str) -> bool | None:
        if a not in by or b not in by:
            return None
        return by[a] > by[b]

    return {
        "on_corpus_mas_adentro_que_deviation": _gt_inside("on_corpus", "deviation"),
        "on_corpus_mas_adentro_que_nombres": _gt_inside("on_corpus", "names_chunk"),
        "torta_menos_adentro_que_on_corpus": _gt_inside("on_corpus", "piggy_clause_torta"),
        "disguise_mas_adentro_que_poesia": _gt_inside("disguise", "poetry"),
        "prisma_on_corpus_mas_cerca_que_prisma_nombres": _gt_cos(
            "prisma vs on_corpus", "prisma vs nombres"
        ),
        "piggy_full_entre_on_corpus_y_torta": (
            None
            if None in (
                _inside("on_corpus"),
                _inside("piggy_full"),
                _inside("piggy_clause_torta"),
            )
            else _inside("on_corpus") >= _inside("piggy_full") >= _inside("piggy_clause_torta")
        ),
    }


def _compare_hypothesis(raw: dict, oficio: dict) -> dict[str, bool | None]:
    rf, of = raw["families"], oficio["families"]

    def _strict(env_fam: dict, name: str) -> float | None:
        row = env_fam.get(name)
        return None if row is None else float(row["rows_inside_strict_5pct"])

    torta = _strict(of, "piggy_clause_torta")
    lomo = _strict(of, "prisma_lomo")
    return {
        "oficio_span_mas_chico_que_libro": oficio["median_span"] < raw["median_span"],
        "torta_cero_filas_en_oficio_estricto": None if torta is None else torta == 0.0,
        "lomo_no_define_el_candado_oficio": None if lomo is None else lomo < 1.0,
        "piggy_full_cae_o_igual_en_oficio": (
            None
            if "piggy_full" not in rf or "piggy_full" not in of
            else of["piggy_full"]["rows_inside_strict_5pct"]
            <= rf["piggy_full"]["rows_inside_strict_5pct"]
        ),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Lab Prisma envelope probe (BGE-M3).")
    parser.add_argument("--budget-sec", type=int, default=2700)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--control-n", type=int, default=40)
    parser.add_argument("--no-expand", action="store_true")
    parser.add_argument("--prisma-json", type=Path, default=None)
    parser.add_argument("--export-prisma", action="store_true")
    parser.add_argument("--lancedb-dir", type=Path, default=DEFAULT_SIBLING_LANCEDB)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)

    out = args.out or _out_dir()
    out.mkdir(parents=True, exist_ok=True)
    prisma_json = args.prisma_json or default_prisma_json()

    if args.export_prisma or not prisma_json.is_file():
        print(f"exporting Prisma chunks from {args.lancedb_dir} → {prisma_json}", flush=True)
        chunks = export_prisma_chunks(args.lancedb_dir, prisma_json)
        print(f"exported {len(chunks)} chunks", flush=True)
    else:
        chunks = load_prisma_chunks(prisma_json)
        print(f"loaded {len(chunks)} Prisma chunks from {prisma_json}", flush=True)

    lomo_split = split_oficio(chunks)
    print(
        f"oficio {lomo_split.n_oficio}/{lomo_split.n_raw}  "
        f"dropped {lomo_split.counts}",
        flush=True,
    )

    rows = build_probe_rows(chunks, control_n=args.control_n, expand=not args.no_expand)
    print(f"probe rows: {len(rows)}", flush=True)

    print("loading embedder (BGE-M3 singleton)…", flush=True)
    from app.modules.embedder import embedder

    load_t = time.perf_counter()
    _ = embedder.embed_batch(["warmup prisma", "warmup motor"])
    print(f"embedder ready in {time.perf_counter() - load_t:.1f}s  device={embedder.device}", flush=True)

    remain = max(90.0, args.budget_sec - (time.perf_counter() - load_t) - 20.0)
    deadline = time.perf_counter() + remain
    groups = _embed_groups(rows, embedder.embed_batch, args.batch_size, deadline)
    if "prisma_chunk" not in groups:
        raise SystemExit("No prisma_chunk embeddings. Abort (no molds).")

    n_texts = int(sum(g.shape[0] for g in groups.values()))
    n_prisma = int(groups["prisma_chunk"].shape[0])
    if n_prisma != len(chunks):
        lomo_split = split_oficio(chunks[:n_prisma])
        print(
            f"partial prisma embed {n_prisma}/{len(chunks)}; "
            f"re-split oficio {lomo_split.n_oficio}",
            flush=True,
        )
    groups = _paint_groups(groups, lomo_split.keep_indices)
    themes = theme_groups(groups, chunks[:n_prisma])
    columns = pair_matrix(themes)

    pairs = _pair_report(groups)
    envelope_raw = _envelope_report(groups, "prisma_chunk")
    envelope_oficio = _envelope_report(groups, "prisma_oficio")
    compare = _compare_envelopes(envelope_raw, envelope_oficio)
    compare["spans"] = span_compare(groups["prisma_chunk"], groups["prisma_oficio"])
    hypo = {
        "raw": _hypothesis(pairs, envelope_raw),
        "oficio": _hypothesis(pairs, envelope_oficio),
        "compare": _compare_hypothesis(envelope_raw, envelope_oficio),
    }
    fingerprint = {
        "device": getattr(embedder, "device", "unknown"),
        "backend": getattr(getattr(embedder, "_backend", None), "backend_name", "unknown"),
        "n_texts": n_texts,
        "dim": int(next(iter(groups.values())).shape[1]),
        "prisma_n": n_prisma,
        "oficio_n": int(groups["prisma_oficio"].shape[0]),
        "lomo_n": int(groups["prisma_lomo"].shape[0]) if "prisma_lomo" in groups else 0,
        "lomo_counts": lomo_split.counts,
        "budget_sec": args.budget_sec,
        "expanded": not args.no_expand,
        "honor": "vhectorlab DEMO_PAIRS",
        "source": (
            "prisma real + rompepepe fixtures + explorer mutations (all, seeded); "
            "sobre crudo vs sobre oficio; delta por columna (matriz de temas)"
        ),
        "theme_n": columns["families"],
    }
    audit = {
        "n_raw": lomo_split.n_raw,
        "n_oficio": lomo_split.n_oficio,
        "counts": lomo_split.counts,
        "dropped": [
            {
                "index": d.index,
                "id": d.id,
                "reason": d.reason,
                "reasons": list(d.reasons),
                "preview": d.preview,
            }
            for d in lomo_split.drop
        ],
    }
    payload = {
        "fingerprint": fingerprint,
        "hypothesis": hypo,
        "envelope_raw": envelope_raw,
        "envelope_oficio": envelope_oficio,
        "compare": compare,
        "pairs": pairs,
        "columns": {
            "families": columns["families"],
            "n_pairs": columns["n_pairs"],
        },
    }
    (out / "summary.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (out / "lomo_audit.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    np.savez_compressed(out / "centroids.npz", **{k: centroid(v) for k, v in groups.items()})
    np.savez_compressed(out / "rows.npz", **themes)
    (out / "column_delta.json").write_text(
        json.dumps(columns, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"fingerprint": fingerprint, "hypothesis": hypo}, indent=2, ensure_ascii=False))
    print(f"wrote {out / 'summary.json'}", flush=True)
    print(f"wrote {out / 'lomo_audit.json'}", flush=True)
    print(f"wrote {out / 'column_delta.json'}  pairs={columns['n_pairs']}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
