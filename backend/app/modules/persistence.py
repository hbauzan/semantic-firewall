"""Chat Persistence module."""
import json
import logging
from pathlib import Path
import asyncio
import uuid
import threading

logger = logging.getLogger(__name__)

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_DATA_DIR.mkdir(parents=True, exist_ok=True)
CHAT_HISTORY_FILE = _DATA_DIR / "chat_history.json"
_MAX_MESSAGES = 100

_HISTORY_LOCK = threading.RLock()

def persist_interaction(user_content: str, assistant_content: str) -> None:
    try:
        with _HISTORY_LOCK:
            if not CHAT_HISTORY_FILE.exists():
                history = []
            else:
                try:
                    history = json.loads(CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
                except Exception as e:
                    logger.warning("Failed to load chat history for persistence: %s", e)
                    history = []
            
            history.append({"id": str(uuid.uuid4()), "role": "user", "content": user_content})
            history.append({"id": str(uuid.uuid4()), "role": "assistant", "content": assistant_content})
            
            payload = json.dumps(history[-_MAX_MESSAGES:], indent=2)
            CHAT_HISTORY_FILE.write_text(payload, encoding="utf-8")
    except Exception as e:
        logger.error("Failed to persist interaction: %s", e)

def load_chat_history() -> list:
    try:
        with _HISTORY_LOCK:
            if not CHAT_HISTORY_FILE.exists():
                return []
            raw = json.loads(CHAT_HISTORY_FILE.read_text(encoding="utf-8"))
            return raw[-_MAX_MESSAGES:]
    except Exception as e:
        logger.warning("Failed to load chat history: %s", e)
        return []

def save_chat_history(messages: list) -> None:
    try:
        with _HISTORY_LOCK:
            payload = json.dumps(messages[-_MAX_MESSAGES:], indent=2)
            CHAT_HISTORY_FILE.write_text(payload, encoding="utf-8")
    except Exception as e:
        logger.error("Failed to save chat history: %s", e)
