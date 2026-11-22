"""Calorie progress ring."""

from __future__ import annotations

import flet as ft

from sehtsnap.core import theme


def calorie_ring(consumed: float, target: int, size: int = 170) -> ft.Stack:
    ratio = min(consumed / target, 1) if target else 0
    remaining = round(target - consumed)
    over = remaining < 0
    return ft.Stack(
        width=size,
        height=size,
        controls=[
            ft.Container(
                width=size,
                height=size,
                content=ft.ProgressRing(
                    value=ratio,
                    stroke_width=14,
                    color=theme.ACCENT if over else theme.PRIMARY,
                    bgcolor=theme.TRACK,
                    semantics_label="Daily calorie progress",
                ),
            ),
            ft.Container(
                width=size,
                height=size,
                alignment=ft.Alignment.CENTER,
                content=ft.Column(
                    tight=True,
                    spacing=0,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Text(
                            f"{abs(remaining):,}",
                            size=30,
                            weight=ft.FontWeight.W_800,
                            color=theme.TEXT,
                        ),
                        ft.Text("kcal over" if over else "kcal left", size=13, color=theme.MUTED),
                    ],
                ),
            ),
        ],
    )
