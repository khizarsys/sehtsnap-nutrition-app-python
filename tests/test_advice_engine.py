from pathlib import Path

import pytest

from sehtsnap.models import FoodItem, HealthCondition
from sehtsnap.services.advice_engine import Severity, get_advice, get_warnings
from sehtsnap.services.nutrition_db import NutritionDB

DATASET = Path(__file__).parents[1] / "assets" / "data" / "south_asian_foods.json"


@pytest.fixture(scope="module")
def db() -> NutritionDB:
    return NutritionDB.from_json(DATASET)


def food(db: NutritionDB, food_id: str) -> FoodItem:
    item = db.get(food_id)
    assert item is not None
    return item


def test_no_conditions_means_no_warnings(db):
    assert get_advice(food(db, "jalebi"), db.foods, []).is_clear


def test_diabetes_warns_on_high_sugar(db):
    warnings = get_warnings(food(db, "jalebi"), [HealthCondition.DIABETES])
    assert any(w.tag == "high_sugar" and w.severity == Severity.LIMIT for w in warnings)


def test_hypertension_warns_on_salt(db):
    warnings = get_warnings(food(db, "nihari"), [HealthCondition.HYPERTENSION])
    assert [w.tag for w in warnings] == ["high_salt"]


def test_cholesterol_warns_on_fried_food(db):
    tags = {w.tag for w in get_warnings(food(db, "samosa"), [HealthCondition.CHOLESTEROL])}
    assert {"fried", "high_fat"} <= tags


def test_limit_warnings_come_first(db):
    warnings = get_warnings(food(db, "mutton_karahi"), [HealthCondition.CHOLESTEROL])
    assert warnings[0].severity == Severity.LIMIT
    assert warnings[-1].severity == Severity.CAUTION


def test_multiple_conditions_are_combined(db):
    conditions = [HealthCondition.DIABETES, HealthCondition.CHOLESTEROL]
    found = {w.condition for w in get_warnings(food(db, "halwa_puri"), conditions)}
    assert found == set(conditions)


def test_alternatives_are_safe_and_lower_calorie(db):
    conditions = [HealthCondition.DIABETES, HealthCondition.HYPERTENSION]
    source = food(db, "halwa_puri")
    advice = get_advice(source, db.foods, conditions)
    assert advice.alternatives
    for alternative in advice.alternatives:
        assert alternative.calories < source.calories
        assert not get_warnings(alternative, conditions)


def test_safe_food_has_no_alternatives(db):
    advice = get_advice(food(db, "kachumber"), db.foods, [HealthCondition.DIABETES])
    assert advice.is_clear
    assert advice.alternatives == []
