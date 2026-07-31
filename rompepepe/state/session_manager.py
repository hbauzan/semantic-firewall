"""Session manager for state persistence, pause/resume, and signal handling.
"""
from datetime import datetime
import json
import logging
from pathlib import Path
import signal
import sys
from typing import Callable, Sequence

from rompepepe.state.models import SessionState

logger = logging.getLogger(__name__)


class SessionManager:
    def __init__(self, vault_path: Path):
        self.vault_path = vault_path
        self.sessions_dir = vault_path / "sessions"
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: SessionState | None = None
        self._on_interrupt_callback: Callable[[], None] | None = None

    def create_session(
        self,
        strategy: str,
        total_steps: int = 0,
        config_grid: Sequence[dict] | None = None,
        initial_target_config: dict | None = None,
        metadata: dict | None = None,
    ) -> SessionState:
        now_str = datetime.now().isoformat()
        session_id = f"{strategy}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        session = SessionState(
            session_id=session_id,
            strategy=strategy,  # type: ignore
            status="running",
            created_at=now_str,
            updated_at=now_str,
            total_steps=total_steps,
            current_step=0,
            config_grid=list(config_grid) if config_grid else [],
            initial_target_config=initial_target_config or {},
            metadata=metadata or {},
        )
        self.current_session = session
        self.save_session(session)
        return session

    def save_session(self, session: SessionState | None = None) -> Path:
        target = session or self.current_session
        if not target:
            raise ValueError("No active session to save")
        
        target.updated_at = datetime.now().isoformat()
        file_path = self.sessions_dir / f"{target.session_id}.json"
        temp_path = file_path.with_suffix(".tmp")
        
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(target.model_dump_json(indent=2))
        temp_path.replace(file_path)
        return file_path

    def load_session(self, session_id: str) -> SessionState:
        file_path = self.sessions_dir / f"{session_id}.json"
        if not file_path.is_file():
            raise FileNotFoundError(f"Session file not found: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        session = SessionState(**data)
        self.current_session = session
        return session

    def list_sessions(self) -> list[SessionState]:
        sessions: list[SessionState] = []
        if not self.sessions_dir.exists():
            return sessions
        for file in sorted(self.sessions_dir.glob("*.json"), reverse=True):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(SessionState(**data))
            except Exception as e:
                logger.warning(f"Could not load session file {file}: {e}")
        return sessions

    def get_latest_interrupted_session(self) -> SessionState | None:
        for session in self.list_sessions():
            if session.status in ("interrupted", "running", "paused"):
                return session
        return None

    def setup_signal_handler(self, cleanup_callback: Callable[[], None] | None = None):
        self._on_interrupt_callback = cleanup_callback

        def handle_sigint(signum, frame):
            print("\n\n[!] Execution interrupted by user (Ctrl+C).")
            if self.current_session:
                self.current_session.status = "interrupted"
                saved_path = self.save_session()
                print(f"[+] Session state saved to: {saved_path}")
                print(f"    Completed steps: {self.current_session.current_step}/{self.current_session.total_steps}")
                print(f"    You can resume this session anytime from the menu.")
            if self._on_interrupt_callback:
                try:
                    self._on_interrupt_callback()
                except Exception as e:
                    logger.error(f"Error during interrupt cleanup: {e}")
            sys.exit(0)

        signal.signal(signal.SIGINT, handle_sigint)
        signal.signal(signal.SIGTERM, handle_sigint)
