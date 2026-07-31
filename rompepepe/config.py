"""Independent configuration loader for rompepepe tool.

Parses rompepepe/.env if present, falling back to system env vars or defaults.
"""
from pathlib import Path
import os
from pydantic import BaseModel, Field


class RompepepeConfig(BaseModel):
    firewall_api_base_url: str = Field(default="http://localhost:8000")
    firewall_x_api_key: str | None = Field(default=None)
    explorer_provider: str = Field(default="ollama")
    explorer_api_key: str | None = Field(default=None)
    explorer_model: str = Field(default="llama3.1")
    vault_storage_path: Path = Field(default=Path("./vault"))


def load_env_file(env_path: Path) -> dict[str, str]:
    env_vars = {}
    if env_path.is_file():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    env_vars[key.strip()] = val.strip().strip("'\"")
    return env_vars


def get_config(base_dir: Path | None = None) -> RompepepeConfig:
    if base_dir is None:
        base_dir = Path(__file__).parent.resolve()
    
    env_path = base_dir / ".env"
    file_vars = load_env_file(env_path)

    def get_var(key: str, default: str) -> str:
        return os.getenv(key, file_vars.get(key, default))

    vault_path_str = get_var("VAULT_STORAGE_PATH", "./vault")
    vault_path = Path(vault_path_str)
    if not vault_path.is_absolute():
        vault_path = (base_dir / vault_path).resolve()

    return RompepepeConfig(
        firewall_api_base_url=get_var("FIREWALL_API_BASE_URL", "http://localhost:8000").rstrip("/"),
        firewall_x_api_key=os.getenv("FIREWALL_X_API_KEY", file_vars.get("FIREWALL_X_API_KEY")) or None,
        explorer_provider=get_var("EXPLORER_PROVIDER", "ollama").lower(),
        explorer_api_key=os.getenv("EXPLORER_API_KEY", file_vars.get("EXPLORER_API_KEY")) or None,
        explorer_model=get_var("EXPLORER_MODEL", "llama3.1"),
        vault_storage_path=vault_path,
    )
