"""Log entries for one meal."""

from __future__ import annotations

from collections.abc import Callable

import flet as ft

from sehtsnap.core import theme
from sehtsnap.models import LogEntry, MealType
from sehtsnap.widgets.common import card, heading, muted


def meal_section(
    meal: MealType, entries: list[LogEntry], on_delete: Callable[[str], object]
) -> ft.Container:
    total = sum(entry.calories for entry in entries)
    rows: list[ft.Control] = [
        ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[heading(meal.value.title(), 16), muted(f"{total:.0f} kcal")],
        )
    ]
    if not entries:
        rows.append(muted("Nothing logged yet"))
    for entry in entries:
        rows.append(
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Column(
                        expand=True,
                        spacing=0,
                        controls=[
                            ft.Text(entry.food_name, size=14, color=theme.TEXT),
                            muted(
                                f"{entry.servings:g} serving{'' if entry.servings == 1 else 's'}"
                                f" · {entry.calories:.0f} kcal",
                                12,
                            ),
                        ],
                    ),
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_color=theme.MUTED,
                        tooltip=f"Remove {entry.food_name}",
                        on_click=lambda _, entry_id=entry.id: on_delete(entry_id),
                    ),
                ],
            )
        )
    return card(ft.Column(spacing=6, controls=rows))
