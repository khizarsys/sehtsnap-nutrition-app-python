"""SehtSnap Flet entry point."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import flet as ft  # noqa: E402

from sehtsnap.core.config import load_settings  # noqa: E402
from sehtsnap.core.routes import Router  # noqa: E402
from sehtsnap.core.state import AppState  # noqa: E402
from sehtsnap.core.theme import BACKGROUND, build_theme  # noqa: E402
from sehtsnap.services.nutrition_db import NutritionDB  # noqa: E402


def main(page: ft.Page) -> None:
    settings = load_settings()
    state = AppState(settings, NutritionDB.from_json(settings.foods_path))
    page.title = "SehtSnap"
    page.theme = build_theme()
    page.theme_mode = ft.ThemeMode.LIGHT
    page.bgcolor = BACKGROUND
    Router(page, state).render()


if __name__ == "__main__":
    ft.run(main, assets_dir=str(ROOT / "assets"))
