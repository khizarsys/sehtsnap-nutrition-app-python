from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from sehtsnap.core.config import Settings
from sehtsnap.core.state import AppState, default_meal, sum_entries
from sehtsnap.core.units import cm_to_inches, inches_to_cm, kg_to_lb, lb_to_kg
from sehtsnap.models import Gender, MealType, UserProfile
from sehtsnap.services.nutrition_db import NutritionDB

DATASET = Path(__file__).parents[1] / "assets" / "data" / "south_asian_foods.json"


@pytest.fixture
def state(tmp_path) -> AppState:
    settings = Settings(local_db_path=tmp_path / "local.db")
    app = AppState(settings, NutritionDB.from_json(DATASET))
    app.sign_up("user@example.com", "password123")
    app.save_profile(UserProfile(age=30, gender=Gender.MALE, height_cm=175, weight_kg=75))
    return app


def test_settings_without_firebase_use_demo_mode():
    assert Settings().demo_mode
    assert not Settings(firebase_api_key="key", firebase_project_id="project").demo_mode
    assert Settings(
        firebase_api_key="key", firebase_project_id="project", force_demo=True
    ).demo_mode


def test_add_and_remove_food(state):
    food = state.nutrition.get("roti")
    entry = state.add_food(food, MealType.BREAKFAST, 2, date.today())
    assert entry.calories == food.calories * 2
    assert sum_entries(state.logs_for(date.today())).calories == food.calories * 2
    state.remove_entry(entry.id)
    assert state.logs_for(date.today()) == []


def test_weekly_calories_fills_seven_days(state):
    today = date.today()
    food = state.nutrition.get("roti")
    state.add_food(food, MealType.LUNCH, 1, today)
    state.add_food(food, MealType.DINNER, 1, today - timedelta(days=6))
    state.add_food(food, MealType.DINNER, 1, today - timedelta(days=7))
    week = state.weekly_calories(today)
    assert len(week) == 7
    assert week[0] == (today - timedelta(days=6), food.calories)
    assert week[-1] == (today, food.calories)
    assert sum(value for _, value in week) == food.calories * 2


def test_listeners_are_notified(state):
    calls = []
    state.subscribe(lambda: calls.append(True))
    state.add_food(state.nutrition.get("roti"), MealType.LUNCH, 1, date.today())
    assert calls


def test_sign_out_clears_session(state):
    state.sign_out()
    assert state.user is None
    assert state.profile is None


@pytest.mark.parametrize(
    ("hour", "meal"),
    [(8, MealType.BREAKFAST), (13, MealType.LUNCH), (20, MealType.DINNER), (17, MealType.SNACKS)],
)
def test_default_meal(hour, meal):
    assert default_meal(datetime(2026, 1, 1, hour)) == meal


def test_unit_round_trips():
    assert inches_to_cm(cm_to_inches(170)) == pytest.approx(170)
    assert lb_to_kg(kg_to_lb(70)) == pytest.approx(70)
