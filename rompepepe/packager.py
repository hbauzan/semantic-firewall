"""Packager module for rompepepe.

Bundles all rompepepe code, configuration, dataset schemas, and latest QA report
into a single LLM/Agent handoff bundle: rompepepe/rompepepe_context.txt
"""
from datetime import datetime
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

ROMPEPEPE_DIR = Path(__file__).resolve().parent
OUTPUT_FILE = ROMPEPEPE_DIR / "rompepepe_context.txt"

FILES_TO_PACK = [
    "run_rompepepe.sh",
    ".env.example",
    "config.py",
    "main.py",
    "client/__init__.py",
    "client/firewall_client.py",
    "client/explorer_client.py",
    "engines/__init__.py",
    "engines/grid_search.py",
    "engines/adaptive_fuzzing.py",
    "state/__init__.py",
    "state/models.py",
    "state/session_manager.py",
    "reports/__init__.py",
    "reports/generator.py",
    "test_dataset/__init__.py",
    "test_dataset/seed_corpus.json",
    "tests/__init__.py",
    "tests/test_client.py",
    "tests/test_engines.py",
    "tests/test_session_manager.py",
]


def build_rompepepe_pack() -> Path:
    lines = []
    lines.append("================================================================================")
    lines.append(" ROMPEPEPE — AGENT HANDOFF CONTEXT PACK BUNDLE")
    lines.append(f" Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append(" Tool: rompepepe (Autonomous Semantic Robustness & Stress Testing Engine)")
    lines.append(" Target: Three-Headed Semantic Firewall REST API")
    lines.append(" Output Path: rompepepe/rompepepe_context.txt")
    lines.append("================================================================================\n")

    packed_count = 0

    for rel_path in FILES_TO_PACK:
        abs_path = ROMPEPEPE_DIR / rel_path
        if abs_path.is_file():
            lines.append("--------------------------------------------------------------------------------")
            lines.append(f" FILE: rompepepe/{rel_path}")
            lines.append("--------------------------------------------------------------------------------")
            try:
                content = abs_path.read_text(encoding="utf-8")
                lines.append(content)
                lines.append("\n")
                packed_count += 1
            except Exception as e:
                lines.append(f"[Error reading file {rel_path}: {e}]\n")

    # Include latest QA report if available in vault/reports/
    reports_dir = ROMPEPEPE_DIR / "vault" / "reports"
    if reports_dir.exists():
        reports = sorted(reports_dir.glob("*.md"), reverse=True)
        if reports:
            latest_report = reports[0]
            lines.append("--------------------------------------------------------------------------------")
            lines.append(f" FILE: rompepepe/vault/reports/{latest_report.name} (LATEST QA REPORT)")
            lines.append("--------------------------------------------------------------------------------")
            try:
                lines.append(latest_report.read_text(encoding="utf-8"))
                lines.append("\n")
                packed_count += 1
            except Exception as e:
                lines.append(f"[Error reading report {latest_report.name}: {e}]\n")

    bundle_content = "\n".join(lines)
    OUTPUT_FILE.write_text(bundle_content, encoding="utf-8")

    logger.info(f"Successfully generated handoff bundle at {OUTPUT_FILE} ({packed_count} files, {len(bundle_content)} bytes)")
    return OUTPUT_FILE


if __name__ == "__main__":
    out = build_rompepepe_pack()
    print(f"[+] Agent Handoff Pack created: {out}")
