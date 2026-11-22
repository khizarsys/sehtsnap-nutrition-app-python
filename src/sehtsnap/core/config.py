"""Load application settings from environment variables and `.env`."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SUPPORTED_AI_PROVIDERS = ("gemini", "openai")
PUBLIC_CONFIG_PATH = PROJECT_ROOT / "assets" / "app_config.json"
PUBLIC_CONFIG_KEYS = ("AI_BACKEND_URL", "FIREBASE_API_KEY", "FIREBASE_PROJECT_ID")


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings."""

    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    firebase_api_key: str = ""
    firebase_project_id: str = ""
    ai_backend_url: str = ""
    gemini_model: str = "gemini-3.5-flash-lite"
    openai_model: str = "gpt-5.4-mini"
    force_demo: bool = False
    local_db_path: Path = PROJECT_ROOT / "data" / "local.db"
    foods_path: Path = PROJECT_ROOT / "assets" / "data" / "south_asian_foods.json"

    @property
    def demo_mode(self) -> bool:
        """Use local storage unless both Firebase values are configured."""
        return self.force_demo or not (self.firebase_api_key and self.firebase_project_id)

    @property
    def active_ai_key(self) -> str:
        """Return the API key for the selected AI provider."""
        return self.openai_api_key if self.ai_provider == "openai" else self.gemini_api_key


def _local_db_path() -> Path:
    """Use Flet's writable app storage in packaged builds."""
    storage = os.getenv("FLET_APP_STORAGE_DATA", "").strip()
    return Path(storage) / "local.db" if storage else PROJECT_ROOT / "data" / "local.db"


def _load_public_config(path: Path) -> None:
    """Apply allowlisted, non-secret values bundled with mobile builds."""
    try:
        values = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return
    if not isinstance(values, dict):
        return
    for key in PUBLIC_CONFIG_KEYS:
        value = values.get(key)
        if isinstance(value, str) and value.strip():
            os.environ.setdefault(key, value.strip())


def load_settings(env_file: Path | None = None, public_config: Path | None = None) -> Settings:
    """Read settings, defaulting an unknown AI provider to Gemini."""
    load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)
    _load_public_config(public_config or PUBLIC_CONFIG_PATH)
    provider = os.getenv("AI_PROVIDER", "gemini").strip().lower()
    if provider not in SUPPORTED_AI_PROVIDERS:
        provider = "gemini"
    return Settings(
        ai_provider=provider,
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        firebase_api_key=os.getenv("FIREBASE_API_KEY", "").strip(),
        firebase_project_id=os.getenv("FIREBASE_PROJECT_ID", "").strip(),
        ai_backend_url=os.getenv("AI_BACKEND_URL", "").strip(),
        gemini_model=os.getenv("GEMINI_MODEL", "").strip() or Settings.gemini_model,
        openai_model=os.getenv("OPENAI_MODEL", "").strip() or Settings.openai_model,
        force_demo=os.getenv("DEMO_MODE", "").strip().lower() in {"1", "true", "yes"},
        local_db_path=_local_db_path(),
    )
