"""Daily food log."""

from __future__ import annotations

import asyncio
from datetime import date, timedelta

import flet as ft

from sehtsnap.core.state import sum_entries
from sehtsnap.models import MealType
from sehtsnap.screens.home import nutrition_summary
from sehtsnap.services.db_service import DatabaseError
from sehtsnap.widgets.common import app_view, heading, muted, show_message
from sehtsnap.widgets.meal_section import meal_section


def build_log(router) -> ft.View:
    state = router.state
    day = state.selected_date

    def change_day(delta: int) -> None:
        state.selected_date = min(day + timedelta(days=delta), date.today())
        router.render()

    async def delete_entry(entry_id: str) -> None:
        try:
            await asyncio.to_thread(state.remove_entry, entry_id)
        except DatabaseError as failure:
            show_message(router.page, str(failure))
            return
        router.render()

    def request_delete(entry_id: str) -> None:
        router.page.run_task(delete_entry, entry_id)

    date_bar = ft.Row(
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        controls=[
            ft.IconButton(
                icon=ft.Icons.CHEVRON_LEFT,
                tooltip="Previous day",
                on_click=lambda _: change_day(-1),
            ),
            heading("Today" if day == date.today() else day.strftime("%a, %d %b %Y"), 16),
            ft.IconButton(
                icon=ft.Icons.CHEVRON_RIGHT,
                tooltip="Next day",
                disabled=day >= date.today(),
                on_click=lambda _: change_day(1),
            ),
        ],
    )
    try:
        entries = state.logs_for(day)
    except DatabaseError as failure:
        return app_view(router, "/log", "Food log", [muted(str(failure))], nav_index=2)
    sections = [
        meal_section(meal, [e for e in entries if e.meal == meal], request_delete)
        for meal in MealType
    ]
    return app_view(
        router,
        "/log",
        "Food log",
        [date_bar, nutrition_summary(sum_entries(entries), state.targets), *sections],
        nav_index=2,
    )
