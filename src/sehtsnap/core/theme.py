"""Visual design tokens and Flet theme."""

from __future__ import annotations

import flet as ft

PRIMARY = "#0F766E"
PRIMARY_SOFT = "#D7EFEA"
ACCENT = "#C2410C"
BACKGROUND = "#FBF7F0"
SURFACE = "#FFFFFF"
TEXT = "#1F2933"
MUTED = "#5F6B76"
BORDER = "#E8E0D4"
PROTEIN = "#0F766E"
CARBS = "#D97706"
FAT = "#BE3455"
WARNING_BG = "#FFF1E6"
LIMIT_BG = "#FDE8EC"
TRACK = "#ECE5DA"


def build_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme_seed=PRIMARY,
        color_scheme=ft.ColorScheme(primary=PRIMARY, secondary=ACCENT, surface=SURFACE),
    )
