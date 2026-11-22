"""Shared layout helpers."""

from __future__ import annotations

import flet as ft

from sehtsnap.core import theme

NAV_ROUTES = ["/home", "/snap", "/log", "/history", "/profile"]
DISCLAIMER = "SehtSnap provides general information and is not medical advice."


def card(content: ft.Control, padding: int = 16, bgcolor: str = theme.SURFACE) -> ft.Container:
    return ft.Container(
        content=content,
        padding=padding,
        bgcolor=bgcolor,
        border=ft.Border.all(1, theme.BORDER),
        border_radius=14,
    )


def heading(text: str, size: int = 18) -> ft.Text:
    return ft.Text(text, size=size, weight=ft.FontWeight.W_700, color=theme.TEXT)


def muted(text: str, size: int = 13) -> ft.Text:
    return ft.Text(text, size=size, color=theme.MUTED)


def show_message(page: ft.Page, message: str) -> None:
    page.show_dialog(ft.SnackBar(content=ft.Text(message), behavior=ft.SnackBarBehavior.FLOATING))


def centered(controls: list[ft.Control], spacing: int = 14) -> ft.ResponsiveRow:
    """Constrain content to a readable column on wide screens."""
    return ft.ResponsiveRow(
        alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            ft.Column(
                col={"xs": 12, "md": 9, "lg": 6},
                spacing=spacing,
                controls=controls,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            )
        ],
    )


def navigation(router, selected: int) -> ft.NavigationBar:
    return ft.NavigationBar(
        selected_index=selected,
        bgcolor=theme.SURFACE,
        indicator_color=theme.PRIMARY_SOFT,
        on_change=lambda event: router.go(NAV_ROUTES[int(event.control.selected_index)]),
        destinations=[
            ft.NavigationBarDestination(
                icon=ft.Icons.HOME_OUTLINED, selected_icon=ft.Icons.HOME, label="Home"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.CAMERA_ALT_OUTLINED, selected_icon=ft.Icons.CAMERA_ALT, label="Snap"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.RESTAURANT_MENU_OUTLINED,
                selected_icon=ft.Icons.RESTAURANT_MENU,
                label="Log",
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.BAR_CHART_OUTLINED, selected_icon=ft.Icons.BAR_CHART, label="History"
            ),
            ft.NavigationBarDestination(
                icon=ft.Icons.PERSON_OUTLINE, selected_icon=ft.Icons.PERSON, label="Profile"
            ),
        ],
    )


def app_view(
    router,
    route: str,
    title: str,
    controls: list[ft.Control],
    nav_index: int | None = None,
    back_route: str | None = None,
    actions: list[ft.Control] | None = None,
) -> ft.View:
    leading = None
    if back_route:
        leading = ft.IconButton(
            icon=ft.Icons.ARROW_BACK, tooltip="Back", on_click=lambda _: router.go(back_route)
        )
    return ft.View(
        route=route,
        bgcolor=theme.BACKGROUND,
        padding=16,
        scroll=ft.ScrollMode.AUTO,
        appbar=ft.AppBar(
            title=ft.Text(title, weight=ft.FontWeight.W_700, color=theme.TEXT),
            bgcolor=theme.BACKGROUND,
            leading=leading,
            automatically_imply_leading=False,
            actions=actions or [],
        ),
        navigation_bar=navigation(router, nav_index) if nav_index is not None else None,
        controls=[centered(controls)],
    )
