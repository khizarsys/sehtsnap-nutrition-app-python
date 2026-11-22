"""Load application settings from environment variables and `.env`."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
SUPPORTED_AI_PROVIDERS = ("gemini", "openai")


@dataclass(frozen=True)
class Settings:
    """Immutable runtime settings."""

    ai_provider: str = "gemini"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    firebase_api_key: str = ""
    firebase_project_id: str = ""
    local_db_path: Path = PROJECT_ROOT / "data" / "local.db"
    foods_path: Path = PROJECT_ROOT / "assets" / "data" / "south_asian_foods.json"

    @property
    def demo_mode(self) -> bool:
        """Use local storage unless both Firebase values are configured."""
        return not (self.firebase_api_key and self.firebase_project_id)

    @property
    def active_ai_key(self) -> str:
        """Return the API key for the selected AI provider."""
        return self.openai_api_key if self.ai_provider == "openai" else self.gemini_api_key


def load_settings(env_file: Path | None = None) -> Settings:
    """Read settings, defaulting an unknown AI provider to Gemini."""
    load_dotenv(env_file or PROJECT_ROOT / ".env", override=False)
    provider = os.getenv("AI_PROVIDER", "gemini").strip().lower()
    if provider not in SUPPORTED_AI_PROVIDERS:
        provider = "gemini"
    return Settings(
        ai_provider=provider,
        gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        firebase_api_key=os.getenv("FIREBASE_API_KEY", "").strip(),
        firebase_project_id=os.getenv("FIREBASE_PROJECT_ID", "").strip(),
    )
