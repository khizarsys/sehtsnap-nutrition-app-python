"""Food nutrition, health advice and logging."""

from __future__ import annotations

import asyncio
from datetime import date

import flet as ft

from sehtsnap.core import theme
from sehtsnap.core.state import default_meal
from sehtsnap.models import MealType
from sehtsnap.services.advice_engine import Severity
from sehtsnap.services.db_service import DatabaseError
from sehtsnap.widgets.common import DISCLAIMER, app_view, card, heading, muted, show_message
from sehtsnap.widgets.food_card import food_card

MIN_SERVINGS = 0.25
MAX_SERVINGS = 5.0


def warning_box(message: str, severity: Severity) -> ft.Container:
    limit = severity == Severity.LIMIT
    return ft.Container(
        padding=10,
        border_radius=10,
        bgcolor=theme.LIMIT_BG if limit else theme.WARNING_BG,
        content=ft.Row(
            controls=[
                ft.Icon(ft.Icons.WARNING_AMBER, color=theme.FAT if limit else theme.CARBS),
                ft.Text(message, expand=True, size=13, color=theme.TEXT),
            ]
        ),
    )


def build_food_detail(router, food_id: str) -> ft.View:
    state = router.state
    food = state.nutrition.get(food_id)
    if food is None:
        return app_view(
            router, f"/food/{food_id}", "Dish", [muted("Dish not found.")], back_route="/snap"
        )
    servings = min(max(round(state.pending_servings * 4) / 4, MIN_SERVINGS), MAX_SERVINGS)
    calories = ft.Text(size=30, weight=ft.FontWeight.W_800, color=theme.ACCENT)
    macros = muted("", 14)
    serving_label = ft.Text(weight=ft.FontWeight.W_600, color=theme.TEXT)

    def refresh_values(value: float) -> None:
        serving_label.value = f"Servings: {value:g}"
        calories.value = f"{food.calories * value:,.0f} kcal"
        macros.value = (
            f"Protein {food.protein_g * value:.0f} g  ·  Carbs {food.carbs_g * value:.0f} g  ·  "
            f"Fat {food.fat_g * value:.0f} g"
        )

    def handle_slider(event) -> None:
        refresh_values(float(event.control.value))
        router.page.update()

    slider = ft.Slider(
        min=MIN_SERVINGS,
        max=MAX_SERVINGS,
        divisions=19,
        value=servings,
        label="{value}",
        active_color=theme.PRIMARY,
        on_change=handle_slider,
    )
    meal = ft.Dropdown(
        label="Meal",
        expand=True,
        value=default_meal().value,
        options=[ft.DropdownOption(key=item.value, text=item.value.title()) for item in MealType],
    )
    add = ft.FilledButton(content="Add to log", icon=ft.Icons.ADD, height=48)

    async def handle_add(_) -> None:
        add.disabled = True
        router.page.update()
        try:
            await asyncio.to_thread(
                state.add_food, food, MealType(meal.value), float(slider.value), date.today()
            )
        except DatabaseError as failure:
            add.disabled = False
            show_message(router.page, str(failure))
            router.page.update()
            return
        state.pending_servings = 1.0
        show_message(router.page, f"{food.name} added to {meal.value}")
        router.go("/log")

    add.on_click = handle_add
    refresh_values(servings)

    def open_alternative(alternative_id: str) -> None:
        state.pending_servings = 1.0
        router.go(f"/food/{alternative_id}")

    advice = state.advice_for(food)
    controls: list[ft.Control] = [
        card(
            ft.Column(
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    heading(food.name, 24),
                    muted(f"1 serving = {food.serving_size}"),
                    calories,
                    macros,
                    serving_label,
                    slider,
                    ft.Row([meal]),
                    add,
                ],
            )
        )
    ]
    if advice.warnings:
        controls.append(heading("Health guidance", 16))
        controls.extend(warning_box(item.message, item.severity) for item in advice.warnings)
    if advice.alternatives:
        controls.append(heading("Healthier alternatives", 16))
        controls.extend(food_card(item, open_alternative) for item in advice.alternatives)
    controls.append(muted(DISCLAIMER, 12))
    return app_view(router, f"/food/{food_id}", "Dish details", controls, back_route="/snap")
