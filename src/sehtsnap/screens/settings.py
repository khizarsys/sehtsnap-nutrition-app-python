"""App settings."""

from __future__ import annotations

import asyncio

import flet as ft

from sehtsnap.core import theme
from sehtsnap.services.db_service import DatabaseError
from sehtsnap.widgets.common import DISCLAIMER, app_view, card, heading, muted, show_message


def build_settings(router) -> ft.View:
    state = router.state

    def set_provider(event) -> None:
        state.ai_provider = event.control.value
        show_message(router.page, f"AI provider set to {state.ai_provider.title()}")

    def set_units(event) -> None:
        state.units = event.control.value
        show_message(router.page, "Units updated")

    provider = ft.Dropdown(
        label="AI provider",
        expand=True,
        value=state.ai_provider,
        on_select=set_provider,
        options=[
            ft.DropdownOption(key="gemini", text="Google Gemini"),
            ft.DropdownOption(key="openai", text="OpenAI"),
        ],
    )
    units = ft.Dropdown(
        label="Units",
        expand=True,
        value=state.units,
        on_select=set_units,
        options=[
            ft.DropdownOption(key="metric", text="Metric (cm, kg)"),
            ft.DropdownOption(key="imperial", text="Imperial (in, lb)"),
        ],
    )

    async def confirm_reset(_) -> None:
        router.page.pop_dialog()
        try:
            await asyncio.to_thread(state.reset_logs)
        except DatabaseError as failure:
            show_message(router.page, str(failure))
            return
        show_message(router.page, "Food logs deleted")

    def ask_reset(_) -> None:
        router.page.show_dialog(
            ft.AlertDialog(
                modal=True,
                title=ft.Text("Delete all food logs?"),
                content=ft.Text("This permanently removes your logged meals."),
                actions=[
                    ft.TextButton(content="Cancel", on_click=lambda _: router.page.pop_dialog()),
                    ft.TextButton(
                        content="Delete",
                        style=ft.ButtonStyle(color=theme.ACCENT),
                        on_click=confirm_reset,
                    ),
                ],
            )
        )

    def logout(_) -> None:
        state.sign_out()
        router.go("/")

    mode = "Demo mode (local storage)" if state.settings.demo_mode else "Firebase cloud sync"
    return app_view(
        router,
        "/settings",
        "Settings",
        [
            card(
                ft.Column(
                    spacing=14,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        heading("Preferences", 16),
                        ft.Row([provider], visible=not state.settings.ai_backend_url),
                        ft.Row([units]),
                    ],
                )
            ),
            card(
                ft.Column(
                    spacing=10,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        heading("Data", 16),
                        muted(f"Storage: {mode}"),
                        ft.OutlinedButton(
                            content="Reset food logs",
                            icon=ft.Icons.DELETE_OUTLINE,
                            on_click=ask_reset,
                        ),
                    ],
                )
            ),
            ft.FilledButton(content="Log out", icon=ft.Icons.LOGOUT, height=46, on_click=logout),
            muted(DISCLAIMER, 12),
        ],
        back_route="/profile",
    )
