"""Profile setup and editing."""

from __future__ import annotations

import asyncio

import flet as ft
from pydantic import ValidationError

from sehtsnap.core import theme
from sehtsnap.core.units import cm_to_inches, inches_to_cm, kg_to_lb, lb_to_kg
from sehtsnap.models import ActivityLevel, Gender, Goal, HealthCondition, UserProfile
from sehtsnap.services.db_service import DatabaseError
from sehtsnap.widgets.common import app_view, card, heading, muted, show_message

ACTIVITY_LABELS = {
    ActivityLevel.SEDENTARY: "Sedentary (little exercise)",
    ActivityLevel.LIGHT: "Light (1-3 days/week)",
    ActivityLevel.MODERATE: "Moderate (3-5 days/week)",
    ActivityLevel.ACTIVE: "Active (6-7 days/week)",
    ActivityLevel.VERY_ACTIVE: "Very active (physical job)",
}
GOAL_LABELS = {Goal.LOSE: "Lose weight", Goal.MAINTAIN: "Maintain weight", Goal.GAIN: "Gain weight"}
CONDITION_LABELS = {
    HealthCondition.DIABETES: "Diabetes",
    HealthCondition.HYPERTENSION: "High blood pressure",
    HealthCondition.CHOLESTEROL: "High cholesterol",
}


def _dropdown(label: str, value: str, options: dict) -> ft.Dropdown:
    return ft.Dropdown(
        label=label,
        value=value,
        expand=True,
        options=[ft.DropdownOption(key=key.value, text=text) for key, text in options.items()],
    )


def _profile_form(router, after_save: str) -> ft.Column:
    state = router.state
    profile = state.profile
    imperial = state.units == "imperial"
    height = profile.height_cm if profile else None
    weight = profile.weight_kg if profile else None
    if imperial and profile:
        height, weight = cm_to_inches(profile.height_cm), kg_to_lb(profile.weight_kg)

    name = ft.TextField(label="Name", value=profile.name if profile else "")
    age = ft.TextField(
        label="Age",
        value=str(profile.age) if profile else "",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )
    gender = _dropdown(
        "Gender",
        profile.gender.value if profile else Gender.MALE.value,
        {Gender.MALE: "Male", Gender.FEMALE: "Female"},
    )
    height_field = ft.TextField(
        label="Height (in)" if imperial else "Height (cm)",
        value=f"{height:g}" if height else "",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )
    weight_field = ft.TextField(
        label="Weight (lb)" if imperial else "Weight (kg)",
        value=f"{round(weight, 1):g}" if weight else "",
        keyboard_type=ft.KeyboardType.NUMBER,
        expand=True,
    )
    activity = _dropdown(
        "Activity level",
        profile.activity_level.value if profile else ActivityLevel.MODERATE.value,
        ACTIVITY_LABELS,
    )
    goal = _dropdown("Goal", profile.goal.value if profile else Goal.MAINTAIN.value, GOAL_LABELS)
    checks = {
        condition: ft.Checkbox(label=label, value=bool(profile and condition in profile.conditions))
        for condition, label in CONDITION_LABELS.items()
    }
    error = ft.Text("", color=theme.ACCENT, visible=False)
    save = ft.FilledButton(content="Save profile", height=46)

    async def handle_save(_) -> None:
        error.visible = False
        try:
            height_value = float(height_field.value or 0)
            weight_value = float(weight_field.value or 0)
            updated = UserProfile(
                name=(name.value or "").strip()[:80],
                age=int(age.value or 0),
                gender=Gender(gender.value),
                height_cm=inches_to_cm(height_value) if imperial else height_value,
                weight_kg=lb_to_kg(weight_value) if imperial else weight_value,
                activity_level=ActivityLevel(activity.value),
                goal=Goal(goal.value),
                conditions=[item for item, check in checks.items() if check.value],
            )
        except (ValueError, ValidationError):
            error.value = "Please enter a valid age (13-100), height and weight."
            error.visible = True
            router.page.update()
            return
        save.disabled = True
        router.page.update()
        try:
            await asyncio.to_thread(state.save_profile, updated)
        except DatabaseError as failure:
            error.value = str(failure)
            error.visible = True
            save.disabled = False
            router.page.update()
            return
        show_message(router.page, "Profile saved")
        router.go(after_save)

    save.on_click = handle_save
    return ft.Column(
        spacing=14,
        horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        controls=[
            name,
            ft.Row([age, gender]),
            ft.Row([height_field, weight_field]),
            activity,
            goal,
            heading("Health conditions", 15),
            muted("Used only to personalize food guidance."),
            *checks.values(),
            error,
            save,
        ],
    )


def build_setup(router) -> ft.View:
    return app_view(
        router,
        "/setup",
        "Your profile",
        [
            muted("This helps calculate your daily calorie and macro targets."),
            card(_profile_form(router, "/home")),
        ],
    )


def build_profile(router) -> ft.View:
    targets = router.state.targets
    summary = muted(f"Daily target: {targets.calories:,} kcal") if targets else muted("")
    return app_view(
        router,
        "/profile",
        "Profile",
        [summary, card(_profile_form(router, "/home"))],
        nav_index=4,
        actions=[
            ft.IconButton(
                icon=ft.Icons.SETTINGS,
                tooltip="Settings",
                on_click=lambda _: router.go("/settings"),
            )
        ],
    )
