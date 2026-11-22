"""Backend settings."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL = "gemini-3.5-flash-lite"


@dataclass(frozen=True)
class BackendSettings:
    gemini_api_key: str
    firebase_project_id: str
    gemini_model: str = DEFAULT_MODEL
    user_hourly_limit: int = 30
    global_daily_limit: int = 500
    max_upload_bytes: int = 8 * 1024 * 1024


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, "").strip()
    if not raw:
        return default
    value = int(raw)
    if value <= 0:
        raise RuntimeError(f"{name} must be greater than zero")
    return value


def load_backend_settings() -> BackendSettings:
    """Load settings and fail at startup if required values are missing."""
    load_dotenv(BACKEND_ROOT / ".env", override=False)
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
    firebase_project_id = os.getenv("FIREBASE_PROJECT_ID", "").strip()
    missing = [
        name
        for name, value in (
            ("GEMINI_API_KEY", gemini_api_key),
            ("FIREBASE_PROJECT_ID", firebase_project_id),
        )
        if not value
    ]
    if missing:
        raise RuntimeError(f"Missing required settings: {', '.join(missing)}")
    return BackendSettings(
        gemini_api_key=gemini_api_key,
        firebase_project_id=firebase_project_id,
        gemini_model=os.getenv("GEMINI_MODEL", "").strip() or DEFAULT_MODEL,
        user_hourly_limit=_positive_int("USER_HOURLY_LIMIT", 30),
        global_daily_limit=_positive_int("GLOBAL_DAILY_LIMIT", 500),
    )
