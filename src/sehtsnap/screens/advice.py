"""Health advice for today's meals."""

from __future__ import annotations

from datetime import date

import flet as ft

from sehtsnap.screens.food_detail import warning_box
from sehtsnap.screens.profile import CONDITION_LABELS
from sehtsnap.services.db_service import DatabaseError
from sehtsnap.widgets.common import DISCLAIMER, app_view, card, heading, muted
from sehtsnap.widgets.food_card import food_card


def build_advice(router) -> ft.View:
    state = router.state
    conditions = state.profile.conditions

    def open_food(food_id: str) -> None:
        state.pending_servings = 1.0
        router.go(f"/food/{food_id}")

    if not conditions:
        body: list[ft.Control] = [
            card(muted("Add a health condition in your profile to get personalized guidance."))
        ]
    else:
        names = ", ".join(CONDITION_LABELS[item] for item in conditions)
        body = [muted(f"Personalized for: {names}")]
        try:
            entries = state.logs_for(date.today())
        except DatabaseError as failure:
            entries = []
            body.append(muted(str(failure)))
        seen: set[str] = set()
        flagged = 0
        for entry in entries:
            food = state.nutrition.get(entry.food_id)
            if food is None or food.id in seen:
                continue
            seen.add(food.id)
            advice = state.advice_for(food)
            if advice.is_clear:
                continue
            flagged += 1
            body.append(heading(food.name, 16))
            body.extend(warning_box(item.message, item.severity) for item in advice.warnings)
            if advice.alternatives:
                body.append(muted("Try instead:"))
                body.extend(food_card(item, open_food) for item in advice.alternatives[:2])
        if not flagged:
            message = "No warnings for today's meals." if entries else "No meals logged today."
            body.append(card(muted(message)))
    body.append(muted(DISCLAIMER, 12))
    return app_view(router, "/advice", "Health advice", body, back_route="/home")
