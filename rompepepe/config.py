"""Independent configuration loader for rompepepe tool.

Parses rompepepe/.env if present, falling back to root workspace .env, system env vars, or defaults.
"""
from pathlib import Path
import os
from pydantic import BaseModel, Field


class RompepepeConfig(BaseModel):
    firewall_api_base_url: str = Field(default="http://localhost:8000")
    firewall_x_api_key: str | None = Field(default=None)
    explorer_provider: str = Field(default="google")
    explorer_api_key: str | None = Field(default=None)
    explorer_model: str = Field(default="gemini-1.5-flash")
    explorer_rpm_limit: int = Field(default=15)
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
    root_env_path = base_dir.parent / ".env"

    file_vars = load_env_file(env_path)
    root_vars = load_env_file(root_env_path)

    # Merged variables dictionary: local .env > root .env > defaults
    merged_vars = {**root_vars, **file_vars}

    def get_var(key: str, default: str) -> str:
        return os.getenv(key, merged_vars.get(key, default))

    # Resolve explorer provider (prefer EXPLORER_PROVIDER, fallback to UPSTREAM_PROVIDER, default 'google')
    provider = get_var("EXPLORER_PROVIDER", get_var("UPSTREAM_PROVIDER", "google")).lower()

    # Resolve API Key based on provider if EXPLORER_API_KEY is missing
    explorer_key = os.getenv("EXPLORER_API_KEY", merged_vars.get("EXPLORER_API_KEY"))
    if not explorer_key:
        if provider == "google":
            explorer_key = os.getenv("GOOGLE_API_KEY", merged_vars.get("GOOGLE_API_KEY")) or os.getenv("GEMINI_API_KEY", merged_vars.get("GEMINI_API_KEY"))
        elif provider == "openai":
            explorer_key = os.getenv("OPENAI_API_KEY", merged_vars.get("OPENAI_API_KEY"))
        elif provider == "anthropic":
            explorer_key = os.getenv("ANTHROPIC_API_KEY", merged_vars.get("ANTHROPIC_API_KEY"))

    # Resolve model
    default_model = "gemini-1.5-flash" if provider == "google" else ("llama3.1" if provider == "ollama" else "gpt-4o")
    if provider == "google":
        model = get_var("EXPLORER_MODEL", get_var("GEMINI_MODEL_ID", "gemini-1.5-flash"))
    else:
        model = get_var("EXPLORER_MODEL", default_model)

    vault_path_str = get_var("VAULT_STORAGE_PATH", "./vault")
    vault_path = Path(vault_path_str)
    if not vault_path.is_absolute():
        vault_path = (base_dir / vault_path).resolve()

    rpm_limit_str = get_var("EXPLORER_RPM_LIMIT", "15")
    try:
        rpm_limit = int(rpm_limit_str)
    except ValueError:
        rpm_limit = 15

    return RompepepeConfig(
        firewall_api_base_url=get_var("FIREWALL_API_BASE_URL", "http://localhost:8000").rstrip("/"),
        firewall_x_api_key=os.getenv("FIREWALL_X_API_KEY", merged_vars.get("FIREWALL_X_API_KEY")) or None,
        explorer_provider=provider,
        explorer_api_key=explorer_key or None,
        explorer_model=model,
        explorer_rpm_limit=rpm_limit,
        vault_storage_path=vault_path,
    )


def update_env_file(key_values: dict[str, str], base_dir: Path | None = None):
    """Programmatically updates keys in rompepepe/.env."""
    if base_dir is None:
        base_dir = Path(__file__).parent.resolve()
    env_path = base_dir / ".env"

    existing_lines = []
    if env_path.is_file():
        with open(env_path, "r", encoding="utf-8") as f:
            existing_lines = f.readlines()

    updated_keys = set()
    new_lines = []

    for line in existing_lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            k, _ = stripped.split("=", 1)
            k = k.strip()
            if k in key_values:
                new_lines.append(f"{k}={key_values[k]}\n")
                updated_keys.add(k)
                continue
        new_lines.append(line)

    for k, v in key_values.items():
        if k not in updated_keys:
            new_lines.append(f"{k}={v}\n")

    with open(env_path, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
