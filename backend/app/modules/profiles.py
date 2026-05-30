"""Configuration Profile Manager — persistent JSON-backed config snapshots.

Profiles are stored as JSON files in backend/data/.
Internal profiles (e.g. _last_used) are prefixed with underscore and
excluded from the public listing returned by list_profiles().

DATA_DIR is resolved as an absolute path relative to this file to guarantee
consistent location regardless of the process working directory.
"""
import json
import logging
import re
from pathlib import Path
from typing import Optional

from app.core.models import ConfigState

logger = logging.getLogger(__name__)

# backend/app/modules/profiles.py  →  3 levels up = backend/
DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

# --- Path Traversal Protection (Audit Finding S3) ---
_SAFE_PROFILE_RE = re.compile(r'^[a-zA-Z0-9_\-]{1,64}$')


class ProfileManager:
    """Static helpers for saving, loading, and listing ConfigState profiles."""

    @staticmethod
    def _validate_name(name: str) -> None:
        """Reject profile names that could escape DATA_DIR via path traversal."""
        if not _SAFE_PROFILE_RE.match(name):
            raise ValueError(f"Invalid profile name: '{name}'")

    @staticmethod
    def save_profile(name: str, state: ConfigState) -> None:
        """Serialize a ConfigState to backend/data/{name}.json."""
        ProfileManager._validate_name(name)
        path = DATA_DIR / f"{name}.json"
        path.write_text(state.model_dump_json(indent=4), encoding="utf-8")
        logger.info("Profile saved: %s", name)

    @staticmethod
    def load_profile(name: str) -> Optional[dict]:
        """Deserialize backend/data/{name}.json → dict, or None if not found."""
        ProfileManager._validate_name(name)
        path = DATA_DIR / f"{name}.json"
        if not path.exists():
            return None
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error("Failed to load profile '%s': %s", name, e)
            return None

    @staticmethod
    def list_profiles() -> list[str]:
        """Return names of all user-visible profiles (underscore-prefixed excluded)."""
        return sorted(
            f.stem for f in DATA_DIR.glob("*.json")
            if not f.name.startswith("_")
        )

    @staticmethod
    def delete_profile(name: str) -> bool:
        """Delete a named profile. Returns True if deleted, False if not found.
        Underscore-prefixed names are protected and cannot be deleted via this method."""
        ProfileManager._validate_name(name)
        if name.startswith("_"):
            logger.warning("Attempted to delete protected profile: %s", name)
            return False
        path = DATA_DIR / f"{name}.json"
        if not path.exists():
            return False
        path.unlink()
        logger.info("Profile deleted: %s", name)
        return True
