"""Weekly calorie history."""

from __future__ import annotations

import math

import flet as ft
import flet_charts as fc

from sehtsnap.core import theme
from sehtsnap.services.db_service import DatabaseError
from sehtsnap.widgets.common import app_view, card, heading, muted


def _legend(color: str, label: str) -> ft.Row:
    return ft.Row(
        tight=True,
        spacing=6,
        controls=[
            ft.Container(width=12, height=12, bgcolor=color, border_radius=3),
            muted(label, 12),
        ],
    )


def build_history(router) -> ft.View:
    state = router.state
    target = state.targets.calories
    try:
        week = state.weekly_calories()
    except DatabaseError as failure:
        return app_view(router, "/history", "History", [muted(str(failure))], nav_index=3)

    highest = max([target, *[value for _, value in week]])
    chart = fc.BarChart(
        height=280,
        max_y=math.ceil(highest * 1.05 / 500) * 500,
        group_spacing=12,
        interactive=True,
        left_axis=fc.ChartAxis(label_size=48, label_spacing=500),
        bottom_axis=fc.ChartAxis(
            label_size=30,
            labels=[
                fc.ChartAxisLabel(value=index, label=ft.Text(day.strftime("%a"), size=12))
                for index, (day, _) in enumerate(week)
            ],
        ),
        groups=[
            fc.BarChartGroup(
                x=index,
                spacing=3,
                rods=[
                    fc.BarChartRod(
                        to_y=value,
                        width=12,
                        color=theme.ACCENT if value > target else theme.PRIMARY,
                        border_radius=3,
                        tooltip=f"{value:,.0f} kcal",
                    ),
                    fc.BarChartRod(
                        to_y=target,
                        width=12,
                        color=theme.TRACK,
                        border_radius=3,
                        tooltip=f"Target {target:,} kcal",
                    ),
                ],
            )
            for index, (_, value) in enumerate(week)
        ],
    )
    logged = [value for _, value in week if value > 0]
    average = sum(logged) / len(logged) if logged else 0
    on_target = sum(1 for value in logged if value <= target)
    return app_view(
        router,
        "/history",
        "History",
        [
            card(
                ft.Column(
                    spacing=12,
                    controls=[
                        heading("Last 7 days", 16),
                        chart,
                        ft.Row(
                            alignment=ft.MainAxisAlignment.CENTER,
                            spacing=16,
                            controls=[
                                _legend(theme.PRIMARY, "Within target"),
                                _legend(theme.ACCENT, "Over target"),
                                _legend(theme.TRACK, "Target"),
                            ],
                        ),
                    ],
                )
            ),
            card(
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    controls=[
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                            controls=[heading(f"{average:,.0f}", 22), muted("avg kcal/day")],
                        ),
                        ft.Column(
                            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                            spacing=0,
                            controls=[
                                heading(f"{on_target}/{len(logged)}", 22),
                                muted("logged days on target"),
                            ],
                        ),
                    ],
                )
            ),
        ],
        nav_index=3,
    )
