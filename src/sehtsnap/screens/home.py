"""Daily dashboard."""

from __future__ import annotations

from datetime import date

import flet as ft

from sehtsnap.core import theme
from sehtsnap.core.state import sum_entries
from sehtsnap.services.db_service import DatabaseError
from sehtsnap.widgets.common import app_view, card, heading, muted
from sehtsnap.widgets.macro_bar import macro_bar
from sehtsnap.widgets.progress_ring import calorie_ring


def nutrition_summary(consumed, targets) -> ft.Container:
    return card(
        ft.Column(
            spacing=14,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[calorie_ring(consumed.calories, targets.calories)],
                ),
                ft.Row(
                    alignment=ft.MainAxisAlignment.CENTER,
                    controls=[
                        muted(f"{consumed.calories:,.0f} of {targets.calories:,} kcal eaten")
                    ],
                ),
                macro_bar("Protein", consumed.protein_g, targets.protein_g, theme.PROTEIN),
                macro_bar("Carbs", consumed.carbs_g, targets.carbs_g, theme.CARBS),
                macro_bar("Fat", consumed.fat_g, targets.fat_g, theme.FAT),
            ],
        )
    )


def build_home(router) -> ft.View:
    state = router.state
    name = state.profile.name.split(" ")[0] if state.profile and state.profile.name else "there"
    try:
        entries = state.logs_for(date.today())
    except DatabaseError as failure:
        return app_view(router, "/home", "Today", [muted(str(failure))], nav_index=0)
    return app_view(
        router,
        "/home",
        "Today",
        [
            heading(f"Assalam o Alaikum, {name}", 22),
            nutrition_summary(sum_entries(entries), state.targets),
            ft.FilledButton(
                content="Snap a meal",
                icon=ft.Icons.CAMERA_ALT,
                height=48,
                on_click=lambda _: router.go("/snap"),
            ),
            ft.OutlinedButton(
                content="View health advice",
                icon=ft.Icons.HEALTH_AND_SAFETY,
                height=46,
                on_click=lambda _: router.go("/advice"),
            ),
        ],
        nav_index=0,
    )
