"""Application version and build identity for startup banner and metadata."""
from __future__ import annotations

import json
import logging
import os
import subprocess
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger("app.startup")

REPO_ROOT = Path(__file__).resolve().parents[3]
MANIFEST_PATH = REPO_ROOT / "manifest.json"


def _git(*args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip() or None
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None


@lru_cache(maxsize=1)
def resolve_version() -> str:
    """Product version from repo manifest.json (without leading ``v``)."""
    if not MANIFEST_PATH.is_file():
        return "unknown"
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "unknown"
    raw = str(data.get("version", "")).strip()
    return raw.lstrip("v") if raw else "unknown"


@lru_cache(maxsize=1)
def resolve_build() -> str:
    """Git short SHA, optional ``-dirty``, or ``SEMANTIC_FIREWALL_BUILD`` env override."""
    env_build = os.environ.get("SEMANTIC_FIREWALL_BUILD", "").strip()
    if env_build:
        return env_build
    sha = _git("rev-parse", "--short", "HEAD")
    if not sha:
        return "dev"
    dirty = _git("status", "--porcelain")
    return f"{sha}-dirty" if dirty else sha


@lru_cache(maxsize=1)
def resolve_branch() -> str | None:
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch in (None, "HEAD"):
        return None
    return branch


def startup_banner() -> str:
    version = resolve_version()
    build = resolve_build()
    branch = resolve_branch()
    parts = [f"version={version}", f"build={build}"]
    if branch:
        parts.append(f"branch={branch}")
    return f"Three-Headed Semantic Firewall  {'  '.join(parts)}"


def log_startup_banner() -> None:
    """Emit version/build as the first application line on stdout and in logs."""
    line = f"=== {startup_banner()} ==="
    print(line, flush=True)
    logger.info(line)
