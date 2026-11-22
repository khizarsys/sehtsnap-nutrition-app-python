"""Macro progress bar."""

from __future__ import annotations

import flet as ft

from sehtsnap.core import theme


def macro_bar(label: str, value: float, target: int, color: str) -> ft.Column:
    return ft.Column(
        spacing=4,
        controls=[
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text(label, size=13, weight=ft.FontWeight.W_600, color=theme.TEXT),
                    ft.Text(f"{value:.0f} / {target} g", size=13, color=theme.MUTED),
                ],
            ),
            ft.ProgressBar(
                value=min(value / target, 1) if target else 0,
                color=color,
                bgcolor=theme.TRACK,
                bar_height=8,
                border_radius=4,
                semantics_label=f"{label} progress",
            ),
        ],
    )
