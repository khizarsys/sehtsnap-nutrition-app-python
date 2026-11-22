from pathlib import Path

import pytest

from sehtsnap.services.nutrition_db import NutritionDB

DATASET = Path(__file__).parents[1] / "assets" / "data" / "south_asian_foods.json"


@pytest.fixture(scope="module")
def db() -> NutritionDB:
    return NutritionDB.from_json(DATASET)


def test_dataset_has_at_least_60_unique_dishes(db):
    assert len(db.foods) >= 60
    assert len({food.id for food in db.foods}) == len(db.foods)


def test_dataset_calories_are_consistent_with_macros(db):
    for food in db.foods:
        estimated = food.protein_g * 4 + food.carbs_g * 4 + food.fat_g * 9
        assert estimated == pytest.approx(food.calories, rel=0.25), food.name


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("biryani", "chicken_biryani"),
        ("daal chawal", "daal_chawal"),
        ("dal chawal", "daal_chawal"),
        ("saag", "sarson_saag"),
        ("nahari", "nihari"),
        ("chapati", "roti"),
        ("بریانی", "chicken_biryani"),
        ("Chiken Biryani", "chicken_biryani"),
    ],
)
def test_match_handles_aliases_and_typos(db, query, expected):
    match = db.match(query)
    assert match is not None
    assert match.food.id == expected


def test_unrelated_dish_has_no_match(db):
    assert db.match("xyzzy qwerty") is None


def test_suggestions_are_distinct_and_limited(db):
    suggestions = db.suggestions("chicken", limit=3)
    assert len(suggestions) == 3
    assert len({item.food.id for item in suggestions}) == 3


def test_search_finds_multiple_foods(db):
    assert {"chicken_karahi", "mutton_karahi"} <= {food.id for food in db.search("karahi")}


def test_blank_search_returns_foods(db):
    assert len(db.search("", limit=5)) == 5
