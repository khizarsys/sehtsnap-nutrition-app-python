"""Tappable food summary."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from sehtsnap.core import theme
from sehtsnap.models import FoodItem
from sehtsnap.widgets.common import muted


def food_card(food: FoodItem, on_open: Callable[[str], None]) -> ft.Container:
    return ft.Container(
        padding=12,
        bgcolor=theme.SURFACE,
        border=ft.Border.all(1, theme.BORDER),
        border_radius=12,
        ink=True,
        on_click=lambda _: on_open(food.id),
        content=ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[
                ft.Column(
                    expand=True,
                    spacing=2,
                    controls=[
                        ft.Text(food.name, size=15, weight=ft.FontWeight.W_600, color=theme.TEXT),
                        muted(food.serving_size, 12),
                    ],
                ),
                ft.Text(
                    f"{food.calories:.0f} kcal", weight=ft.FontWeight.W_700, color=theme.ACCENT
                ),
            ],
        ),
    )
