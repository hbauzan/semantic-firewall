#!/usr/bin/env python3
"""audit_precision.py — Universal Numerical Purity & Truncation Auditor.

Scans any codebase (Python, JavaScript, TypeScript, C/C++, Rust) to detect
lossy decimal truncation, coward roundings, and half-precision downcasts that
silently corrupt high-dimensional coordinate intervals and semantic containment.

Zero external dependencies (uses only the Python standard library).
Usage:
    python tools/audit_precision.py [PATH]
    python tools/audit_precision.py . --json
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

# Directories to skip unconditionally
IGNORED_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        "dist",
        "build",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".idea",
        ".vscode",
        ".gemini",
        "artifacts",
        "scratch",
    }
)

# Supported extensions
CODE_EXTENSIONS = frozenset(
    {
        ".py",
        ".js",
        ".ts",
        ".jsx",
        ".tsx",
        ".c",
        ".cpp",
        ".h",
        ".hpp",
        ".rs",
        ".go",
    }
)


@dataclass
class RuleViolation:
    file_path: str
    line_number: int
    line_content: str
    rule_id: str
    severity: str
    description: str
    suggested_fix: str


# Regex detection rules
PATTERNS = (
    (
        "RULE-01-ROUND",
        "CRITICAL",
        r"\bround\s*\(",
        "Prohibited rounding function `round(...)` in computation path.",
        "Remove `round()` and keep raw native IEEE 754 float32/float64 scalar.",
    ),
    (
        "RULE-02-NUMPY-ROUND",
        "CRITICAL",
        r"\b(np|numpy|torch)\.round\s*\(",
        "Prohibited tensor rounding `np.round(...)` or `torch.round(...)`.",
        "Remove tensor rounding; retain raw continuous coordinates.",
    ),
    (
        "RULE-03-FORMAT-FLOAT",
        "HIGH",
        r"(:[0-9]*\.[0-9]+f|%[0-9]*\.[0-9]+f)",
        "Fixed-decimal float string formatting (e.g. `:.4f`, `:.6f`, `:.2f`).",
        "Use full IEEE 754 precision `f'{float(val):.17g}'` or `str(float(val))`.",
    ),
    (
        "RULE-04-JS-TOFIXED",
        "HIGH",
        r"\.toFixed\s*\(",
        "JavaScript `.toFixed(...)` truncates precision.",
        "Use `Number(x)` or `x.toPrecision(17)`. Truncate only at terminal DOM presentation.",
    ),
    (
        "RULE-05-JS-MATH-ROUND",
        "HIGH",
        r"Math\.(round|floor|ceil)\s*\(",
        "JavaScript `Math.round/floor/ceil` collapses floating-point coordinates.",
        "Retain continuous float values in memory and WebGL buffers.",
    ),
    (
        "RULE-06-FLOAT16-DOWNCAST",
        "HIGH",
        r"\b(float16|bfloat16|Float16Array|\.half\(\)|\.to\(torch\.float16\)|astype\(\s*np\.float16\))",
        "Premature float16/bfloat16 downcasting (machine epsilon ~1e-3 erases interval gaps).",
        "Preserve native Float32 precision (`float32` / `torch.float32`) for coordinates.",
    ),
)

COMPILED_PATTERNS = tuple(
    (rule_id, severity, re.compile(pat), desc, fix)
    for rule_id, severity, pat, desc, fix in PATTERNS
)


def should_scan_file(path: Path) -> bool:
    if path.suffix.lower() not in CODE_EXTENSIONS:
        return False
    # Check if any parent directory is ignored
    for part in path.parts:
        if part in IGNORED_DIRS:
            return False
    return True


def audit_file(path: Path) -> Iterator[RuleViolation]:
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line_idx, line in enumerate(f, start=1):
                clean_line = line.strip()
                # Skip pure comments
                if clean_line.startswith(("#", "//", "/*", "*")):
                    continue

                for rule_id, severity, regex, desc, fix in COMPILED_PATTERNS:
                    if regex.search(clean_line):
                        yield RuleViolation(
                            file_path=str(path),
                            line_number=line_idx,
                            line_content=clean_line,
                            rule_id=rule_id,
                            severity=severity,
                            description=desc,
                            suggested_fix=fix,
                        )
    except Exception as err:
        sys.stderr.write(f"Warning: could not read {path}: {err}\n")


def scan_directory(root_dir: Path) -> list[RuleViolation]:
    violations: list[RuleViolation] = []
    for dirpath, dirnames, filenames in os.walk(root_dir):
        # Prune ignored directories in-place to avoid descending into them
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]

        for fname in filenames:
            fpath = Path(dirpath) / fname
            if should_scan_file(fpath):
                violations.extend(audit_file(fpath))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit codebases for precision-mutilating decimal truncations and roundings."
    )
    parser.add_argument(
        "target",
        nargs="?",
        default=".",
        help="Root directory or file to scan (default: current directory)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON for automated consumption by AI agents",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Only output summary without individual violations",
    )

    args = parser.parse_args()
    target_path = Path(args.target).resolve()

    if not target_path.exists():
        sys.stderr.write(f"Error: Target path does not exist: {target_path}\n")
        return 2

    violations = (
        list(audit_file(target_path))
        if target_path.is_file()
        else scan_directory(target_path)
    )

    if args.json:
        output_data = {
            "target": str(target_path),
            "total_violations": len(violations),
            "violations": [asdict(v) for v in violations],
        }
        print(json.dumps(output_data, indent=2))
        return 1 if violations else 0

    print("=" * 80)
    print("  UNIVERSAL NUMERICAL PURITY AUDITOR (IEEE 754 Full-Mantissa Enforcer)")
    print(f"  Target: {target_path}")
    print("=" * 80)

    if not violations:
        print("\n[OK] ZERO PRECISION MUTILATIONS DETECTED. Codebase complies with IEEE 754 purity.\n")
        return 0

    # Group by file
    grouped: dict[str, list[RuleViolation]] = {}
    for v in violations:
        grouped.setdefault(v.file_path, []).append(v)

    if not args.quiet:
        for file_path, file_violations in grouped.items():
            rel_path = file_path
            try:
                rel_path = str(Path(file_path).relative_to(target_path))
            except ValueError:
                pass

            print(f"\n📁 {rel_path} ({len(file_violations)} violations):")
            for v in file_violations:
                color_tag = "[CRITICAL]" if v.severity == "CRITICAL" else "[HIGH]"
                print(f"  L{v.line_number}: {color_tag} {v.rule_id} — {v.description}")
                print(f"     Code: {v.line_content}")
                print(f"     Fix:  {v.suggested_fix}")

    print("\n" + "=" * 80)
    print(f"AUDIT SUMMARY: {len(violations)} violations across {len(grouped)} files.")
    print("Action required: Refactor marked lines to preserve full IEEE 754 float32 precision.")
    print("=" * 80 + "\n")

    return 1


if __name__ == "__main__":
    sys.exit(main())
