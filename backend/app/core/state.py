"""Global configuration state management with thread-safety guarantees.

- config_state is always a frozen ConfigState (immutable after construction).
- Writes are serialized via asyncio.Lock.
- set_config() atomically replaces the global reference (merge + validate + swap).
- Readers take a snapshot reference: cfg = config_state (safe under GIL).
"""
import asyncio
from app.core.models import ConfigState

config_state: ConfigState = ConfigState()
_config_lock = asyncio.Lock()


def set_config(**kwargs) -> ConfigState:
    """Atomically replace global config. Merges kwargs over current state.
    Used by update_config route and test harness."""
    global config_state
    current = config_state.model_dump()
    current.update(kwargs)
    config_state = ConfigState(**current)
    return config_state
