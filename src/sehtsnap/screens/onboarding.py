"""Welcome screen."""

from __future__ import annotations

import flet as ft

from sehtsnap.core import theme
from sehtsnap.widgets.common import DISCLAIMER, centered, muted


def _feature(icon: ft.IconData, title: str, text: str) -> ft.Row:
    return ft.Row(
        spacing=14,
        controls=[
            ft.Container(
                width=44,
                height=44,
                border_radius=12,
                bgcolor=theme.PRIMARY_SOFT,
                alignment=ft.Alignment.CENTER,
                content=ft.Icon(icon, color=theme.PRIMARY),
            ),
            ft.Column(
                expand=True,
                spacing=1,
                controls=[
                    ft.Text(title, weight=ft.FontWeight.W_700, color=theme.TEXT),
                    muted(text),
                ],
            ),
        ],
    )


def build_onboarding(router) -> ft.View:
    return ft.View(
        route="/",
        bgcolor=theme.BACKGROUND,
        padding=24,
        scroll=ft.ScrollMode.AUTO,
        vertical_alignment=ft.MainAxisAlignment.CENTER,
        controls=[
            centered(
                spacing=20,
                controls=[
                    ft.Text("SehtSnap", size=38, weight=ft.FontWeight.W_800, color=theme.PRIMARY),
                    ft.Text(
                        "Know what is on your plate, from biryani to daal.",
                        size=20,
                        weight=ft.FontWeight.W_600,
                        color=theme.TEXT,
                    ),
                    _feature(
                        ft.Icons.CAMERA_ALT,
                        "Snap your meal",
                        "AI recognizes South Asian dishes from a photo.",
                    ),
                    _feature(
                        ft.Icons.RESTAURANT_MENU,
                        "Track calories and macros",
                        "Log desi meals with realistic serving sizes.",
                    ),
                    _feature(
                        ft.Icons.HEALTH_AND_SAFETY,
                        "Eat with your health in mind",
                        "See guidance for diabetes, blood pressure and cholesterol.",
                    ),
                    ft.FilledButton(
                        content="Get started", height=48, on_click=lambda _: router.go("/auth")
                    ),
                    muted(DISCLAIMER, 12),
                ],
            )
        ],
    )
