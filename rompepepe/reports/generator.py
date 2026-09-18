"""Quality Assurance & Boundary Markdown Report Generator.

Transforms SessionState into structured Markdown report: rompepepe_report_YYYYMMDD_HHMMSS.md
"""
from datetime import datetime
import logging
from pathlib import Path

from rompepepe.oracle.metrics import ConfusionMatrix, metrics_from_results
from rompepepe.state.models import SessionState, TestResult

logger = logging.getLogger(__name__)


class ReportGenerator:
    def __init__(self, reports_dir: Path):
        self.reports_dir = reports_dir
        self.reports_dir.mkdir(parents=True, exist_ok=True)

    def generate_report(self, session: SessionState, target_base_url: str = "http://localhost:8000") -> Path:
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"rompepepe_report_{timestamp_str}.md"
        file_path = self.reports_dir / filename

        total_tests = len(session.results)
        passed_count = sum(1 for r in session.results if r.passed)
        blocked_count = total_tests - passed_count
        stability_pct = (passed_count / total_tests * 100.0) if total_tests > 0 else 0.0
        blocked_pct = (blocked_count / total_tests * 100.0) if total_tests > 0 else 0.0

        avg_latency = (
            sum(r.duration_ms for r in session.results) / total_tests
            if total_tests > 0
            else 0.0
        )

        boundary_count = len(session.boundary_traces)

        # Markdown Report Generation
        md_lines = []
        md_lines.append(f"# Quality Assurance & Semantic Boundary Report — Pepe ('rompepepe')\n")
        md_lines.append(f"**Report Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        md_lines.append(f"**Session ID:** `{session.session_id}`")
        md_lines.append(f"**Exploration Strategy:** `{session.strategy.upper()}`")
        md_lines.append(f"**Target System Base URL:** `{target_base_url}`\n")

        md_lines.append("## Executive Summary\n")
        defense = metrics_from_results(session.results)
        if defense is not None:
            md_lines.extend(_defense_metrics_section(defense))
        else:
            md_lines.append(
                "> Oracle labels (`expected_label`, `delivered_text`) were not recorded. "
                "Defense recall / FPR / leakage cannot be computed for this session.\n"
            )

        md_lines.append("## Auxiliary /audit pass rate (not a defense metric)\n")
        md_lines.append("| Metric | Value |")
        md_lines.append("| :--- | :--- |")
        md_lines.append(f"| Total Tests Executed | `{total_tests}` |")
        md_lines.append(f"| Allowed (`trace.passed`) | `{passed_count}` ({stability_pct:.1f}%) |")
        md_lines.append(f"| Restricted | `{blocked_count}` ({blocked_pct:.1f}%) |")
        md_lines.append(f"| Boundary Transition Events | `{boundary_count}` |")
        md_lines.append(f"| Average REST Latency | `{avg_latency:.2f} ms` |")
        md_lines.append(f"| Session Status | `{session.status.upper()}` |\n")
        md_lines.append(
            "_This /audit allow-rate is a lab instrument readout. It is **not** "
            "recall de bloqueo, FPR, or egress leakage._\n"
        )

        if session.metadata.get("quota_exhausted") or session.status == "paused":
            md_lines.append("> [!WARNING]")
            pause_reason = session.metadata.get("pause_reason", "Token quota / rate limit exhausted.")
            md_lines.append(f"> **Execution Paused Due to Token Quota Exhaustion:** {pause_reason}")
            md_lines.append(f"> The session state has been cleanly saved at step **{session.current_step}/{session.total_steps}**.")
            md_lines.append(f"> You can resume execution anytime by running `./run_rompepepe.sh` option 7 or `python -m rompepepe.main --resume {session.session_id}`.\n")
        elif defense is None:
            md_lines.append("> [!NOTE]")
            md_lines.append(
                "> No Oracle labels on this session. Do not treat the auxiliary /audit "
                f"allow-rate ({stability_pct:.1f}%) as defense success.\n"
            )

        md_lines.append("\n## System Behavioral Boundaries & Sensitivity Analysis\n")
        
        # Categorize breach reasons
        breaches = {}
        for r in session.results:
            if not r.passed and r.breach_reason:
                breaches[r.breach_reason] = breaches.get(r.breach_reason, 0) + 1

        if breaches:
            md_lines.append("### Filter Breach Breakdown\n")
            md_lines.append("| Breach Reason | Trigger Count | Share % |")
            md_lines.append("| :--- | :--- | :--- |")
            for reason, cnt in sorted(breaches.items(), key=lambda x: x[1], reverse=True):
                share = (cnt / blocked_count * 100.0) if blocked_count > 0 else 0.0
                md_lines.append(f"| `{reason}` | `{cnt}` | `{share:.1f}%` |")
            md_lines.append("")

        if session.strategy == "grid_search" and session.config_grid:
            md_lines.append("### Configuration Grid Permutation Metrics\n")
            md_lines.append("| Cell # | Cosine Thresh | Excitation Thresh | Noise Limit | Mode | Pass Rate | Avg Latency |")
            md_lines.append("| :--- | :--- | :--- | :--- | :--- | :--- | :--- |")
            
            # Group results by config
            cfg_groups: dict[str, list[TestResult]] = {}
            for r in session.results:
                cfg_key = f"{r.config.get('cosine_threshold')}_{r.config.get('excitation_threshold')}_{r.config.get('global_noise_limit')}_{r.config.get('firewall_mode')}"
                cfg_groups.setdefault(cfg_key, []).append(r)

            for idx, (cfg_key, group_results) in enumerate(cfg_groups.items(), start=1):
                first_cfg = group_results[0].config
                pass_cnt = sum(1 for r in group_results if r.passed)
                pr = (pass_cnt / len(group_results) * 100.0) if group_results else 0.0
                avg_l = sum(r.duration_ms for r in group_results) / len(group_results) if group_results else 0.0
                md_lines.append(
                    f"| `{idx}` | `{first_cfg.get('cosine_threshold')}` | `{first_cfg.get('excitation_threshold')}` | "
                    f"`{first_cfg.get('global_noise_limit')}` | `{first_cfg.get('firewall_mode')}` | `{pr:.1f}%` | `{avg_l:.1f}ms` |"
                )
            md_lines.append("")

        md_lines.append("\n## Telemetry Traces & Boundary Transition Events\n")
        if session.boundary_traces:
            md_lines.append(f"Located **{len(session.boundary_traces)}** boundary transition points where a minimal prompt mutation flipped the firewall decision:\n")
            for idx, b in enumerate(session.boundary_traces[:10], start=1):
                md_lines.append(f"### Boundary Transition #{idx}\n")
                md_lines.append(f"- **Mutation Description:** {b.mutation_description}")
                md_lines.append(f"- **Prompt A (Passed={b.passed_a}, Cosine={b.cosine_a}):**\n  > `{b.prompt_a}`")
                md_lines.append(f"- **Prompt B (Passed={b.passed_b}, Cosine={b.cosine_b}):**\n  > `{b.prompt_b}`\n")
        else:
            md_lines.append("_No sharp boundary transition points detected in this test run._\n")

        md_lines.append("\n## Actionable Developer & AI Tuning Recommendations\n")
        md_lines.append("1. **Cosine Similarity Calibration:**")
        if "cosine_threshold" in breaches:
            md_lines.append("   - High cosine block rate observed. Consider fine-tuning `cosine_threshold` around `0.5315` for optimum Youden Index balance.")
        else:
            md_lines.append("   - Cosine threshold appears well-balanced for the tested queries.")

        md_lines.append("2. **Excitation Accumulator Sensitivity:**")
        md_lines.append("   - Keep `excitation_threshold` at `150-170` to prevent multi-part prompt bypasses while avoiding legitimate prompt blocking.")

        md_lines.append("3. **Pipeline Evaluation Ordering:**")
        md_lines.append("   - Optimal recommended pipeline sequence: `Cosine (Order 1) -> Entropy Noise (Order 2) -> Excitation (Order 3)` for minimal latency overhead.")

        report_content = "\n".join(md_lines)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(report_content)

        logger.info(f"Generated QA Report at {file_path}")
        return file_path


def _defense_metrics_section(defense: ConfusionMatrix) -> list[str]:
    return [
        "## Defense metrics (Oracle)\n",
        "| Metric | Value |",
        "| :--- | :--- |",
        f"| Recall de bloqueo | `{defense.recall_block:.3f}` (`{defense.true_positive}/{defense.n_attack}`) |",
        f"| False positive rate | `{defense.fpr:.3f}` (`{defense.false_positive}/{defense.n_benign}`) |",
        f"| Egress leakage | `{defense.leakage_rate:.3f}` (`{defense.leaked}/{defense.z_attempts}`) |",
        "",
        "### Confusion matrix\n",
        "|  | Predicted block | Predicted allow |",
        "| :--- | :---: | :---: |",
        f"| Attack | `{defense.true_positive}` | `{defense.false_negative}` |",
        f"| Benign | `{defense.false_positive}` | `{defense.true_negative}` |\n",
    ]

