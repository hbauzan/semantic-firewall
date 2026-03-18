"""
Async Load Testing Suite — Three-Headed Semantic Firewall
=======================================================

Extracts hard performance metrics (Latency, RPS, Error Rate) by hammering
the /audit endpoint under concurrent load with three distinct payload profiles.

Usage:
    # Start the backend first:
    #   cd backend && .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
    #
    # Then run the suite:
    #   .venv/bin/python tests/load_test_suite.py
    #
    # Optional flags:
    #   --base-url http://192.168.1.10:8000   (default: http://localhost:8000)
    #   --requests 500                         (total requests per profile, default: 200)
    #   --output results/my_report.csv         (default: tests/metrics_report.csv)
"""

import argparse
import asyncio
import csv
import os
import statistics
import sys
import time
from dataclasses import dataclass, field

import httpx

# ---------------------------------------------------------------------------
# Payload Profiles
# ---------------------------------------------------------------------------

PROFILES: dict[str, dict] = {
    "short_query": {
        "description": "< 5 words — triggers adaptive factor",
        "payload": {"query": "tire pressure PSI"},
    },
    "long_query": {
        "description": "> 50 words with punctuation — multi-clause segmentation",
        "payload": {
            "query": (
                "Please provide a detailed technical explanation of the recommended "
                "tire pressure for the rear axle of the vehicle. Include the nominal "
                "PSI value, the acceptable tolerance range, and any environmental "
                "factors such as ambient temperature or altitude that could affect "
                "the reading. Also clarify whether nitrogen-filled tires require a "
                "different baseline pressure compared to standard air-filled tires; "
                "and mention the sensor calibration procedure if applicable."
            )
        },
    },
    "overflow_query": {
        "description": "> 100 words NO punctuation — forces 15-word overflow chunking",
        "payload": {
            "query": (
                "tire pressure rear axle nominal value tolerance range environmental "
                "factors ambient temperature altitude reading nitrogen filled tires "
                "different baseline pressure standard air filled sensor calibration "
                "procedure maintenance interval recommended schedule seasonal "
                "adjustment cold weather hot weather highway driving city driving "
                "load capacity maximum payload towing conditions spare tire "
                "specifications temporary use limitations speed restrictions "
                "replacement criteria tread depth measurement wear indicator bars "
                "rotation pattern cross rotation front to rear alignment angles "
                "camber caster toe settings impact on tire longevity fuel economy "
                "relationship rolling resistance coefficient braking distance wet "
                "conditions dry conditions emergency stopping performance"
            )
        },
    },
}

# ---------------------------------------------------------------------------
# Result Container
# ---------------------------------------------------------------------------


@dataclass
class LoadTestResult:
    profile: str
    concurrency: int
    total_requests: int
    latencies: list[float] = field(default_factory=list)
    status_codes: list[int] = field(default_factory=list)
    wall_time: float = 0.0

    @property
    def success_count(self) -> int:
        return sum(1 for s in self.status_codes if 200 <= s < 300)

    @property
    def failure_count(self) -> int:
        return sum(1 for s in self.status_codes if s >= 400 or s == 0)

    @property
    def timeout_count(self) -> int:
        return sum(1 for s in self.status_codes if s == 0)

    @property
    def avg_latency(self) -> float:
        return statistics.mean(self.latencies) if self.latencies else 0.0

    @property
    def min_latency(self) -> float:
        return min(self.latencies) if self.latencies else 0.0

    @property
    def max_latency(self) -> float:
        return max(self.latencies) if self.latencies else 0.0

    @property
    def p95_latency(self) -> float:
        if len(self.latencies) < 2:
            return self.avg_latency
        sorted_lats = sorted(self.latencies)
        idx = int(len(sorted_lats) * 0.95)
        return sorted_lats[min(idx, len(sorted_lats) - 1)]

    @property
    def rps(self) -> float:
        return self.total_requests / self.wall_time if self.wall_time > 0 else 0.0

    @property
    def error_rate(self) -> float:
        return (self.failure_count / self.total_requests * 100) if self.total_requests > 0 else 0.0


# ---------------------------------------------------------------------------
# Load Test Engine
# ---------------------------------------------------------------------------


async def _send_request(
    client: httpx.AsyncClient,
    url: str,
    payload: dict,
    semaphore: asyncio.Semaphore,
) -> tuple[float, int]:
    """Send a single request, return (latency_seconds, status_code)."""
    async with semaphore:
        start = time.perf_counter()
        try:
            resp = await client.post(url, json=payload, timeout=30.0)
            elapsed = time.perf_counter() - start
            return elapsed, resp.status_code
        except httpx.TimeoutException:
            elapsed = time.perf_counter() - start
            return elapsed, 0  # 0 = timeout
        except httpx.ConnectError:
            elapsed = time.perf_counter() - start
            return elapsed, 0


async def run_load_test(
    base_url: str,
    concurrency: int,
    total_requests: int,
    profile_name: str,
) -> LoadTestResult:
    """Fire `total_requests` against /audit with the given concurrency cap."""
    profile = PROFILES[profile_name]
    url = f"{base_url}/audit"
    semaphore = asyncio.Semaphore(concurrency)

    result = LoadTestResult(
        profile=profile_name,
        concurrency=concurrency,
        total_requests=total_requests,
    )

    async with httpx.AsyncClient() as client:
        # Warm-up: single request to ensure embedder is loaded
        try:
            await client.post(url, json=profile["payload"], timeout=60.0)
        except Exception:
            pass

        tasks = [
            _send_request(client, url, profile["payload"], semaphore)
            for _ in range(total_requests)
        ]

        wall_start = time.perf_counter()
        responses = await asyncio.gather(*tasks)
        result.wall_time = time.perf_counter() - wall_start

    for latency, status in responses:
        result.latencies.append(latency)
        result.status_codes.append(status)

    return result


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

HEADER = [
    "Profile",
    "Concurrency",
    "Total Reqs",
    "Success",
    "Failures",
    "Timeouts",
    "Error %",
    "Min (ms)",
    "Avg (ms)",
    "P95 (ms)",
    "Max (ms)",
    "RPS",
    "Wall (s)",
]


def result_to_row(r: LoadTestResult) -> list[str]:
    return [
        r.profile,
        str(r.concurrency),
        str(r.total_requests),
        str(r.success_count),
        str(r.failure_count),
        str(r.timeout_count),
        f"{r.error_rate:.1f}",
        f"{r.min_latency * 1000:.1f}",
        f"{r.avg_latency * 1000:.1f}",
        f"{r.p95_latency * 1000:.1f}",
        f"{r.max_latency * 1000:.1f}",
        f"{r.rps:.1f}",
        f"{r.wall_time:.2f}",
    ]


def print_table(results: list[LoadTestResult]) -> None:
    rows = [HEADER] + [result_to_row(r) for r in results]
    col_widths = [max(len(row[i]) for row in rows) for i in range(len(HEADER))]

    def fmt_row(row: list[str]) -> str:
        return " | ".join(cell.rjust(w) for cell, w in zip(row, col_widths))

    separator = "-+-".join("-" * w for w in col_widths)

    print()
    print(fmt_row(rows[0]))
    print(separator)
    for row in rows[1:]:
        print(fmt_row(row))
    print()


def write_csv(results: list[LoadTestResult], path: str) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(HEADER)
        for r in results:
            writer.writerow(result_to_row(r))
    print(f"CSV report written to: {path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main(base_url: str, total_requests: int, csv_path: str) -> None:
    concurrency_levels = [10, 50, 200]
    profile_names = list(PROFILES.keys())
    all_results: list[LoadTestResult] = []

    # Preflight: check server is reachable
    print(f"Connecting to {base_url}/health ...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(f"{base_url}/health", timeout=10.0)
            health = resp.json()
            print(f"  Status: {health.get('status')}  |  Corpus: {health.get('corpus_chunks')} chunks  |  Embedder: {'OK' if health.get('embedder_loaded') else 'MISSING'}")
            if not health.get("embedder_loaded"):
                print("  WARNING: Embedder not loaded — results will be all errors.")
            if health.get("corpus_chunks", 0) == 0:
                print("  WARNING: Corpus is empty — /audit will return 0 activations (still valid for latency benchmarks).")
        except Exception as e:
            print(f"  FATAL: Cannot reach backend — {e}")
            print("  Start the server first: cd backend && .venv/bin/uvicorn app.main:app --port 8000")
            sys.exit(1)

    print()
    total_runs = len(concurrency_levels) * len(profile_names)
    run_idx = 0

    for conc in concurrency_levels:
        for pname in profile_names:
            run_idx += 1
            desc = PROFILES[pname]["description"]
            print(f"[{run_idx}/{total_runs}] {pname} @ {conc} concurrent  ({desc})")

            result = await run_load_test(base_url, conc, total_requests, pname)
            all_results.append(result)

            print(
                f"         -> {result.success_count}/{result.total_requests} OK  |  "
                f"Avg {result.avg_latency*1000:.0f}ms  |  "
                f"P95 {result.p95_latency*1000:.0f}ms  |  "
                f"RPS {result.rps:.1f}"
            )

    print("\n" + "=" * 80)
    print("LOAD TEST RESULTS — Three-Headed Semantic Firewall")
    print("=" * 80)
    print_table(all_results)
    write_csv(all_results, csv_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Async load test suite for Semantic Firewall")
    parser.add_argument("--base-url", default="http://localhost:8000", help="Backend base URL")
    parser.add_argument("--requests", type=int, default=200, help="Total requests per profile/concurrency combo")
    parser.add_argument("--output", default="tests/metrics_report.csv", help="CSV output path")
    args = parser.parse_args()

    asyncio.run(main(args.base_url, args.requests, args.output))
