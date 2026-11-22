import pytest
from pydantic import ValidationError

from sehtsnap.models import ActivityLevel, Gender, Goal, UserProfile
from sehtsnap.services.calorie_calculator import (
    calculate_bmr,
    calculate_targets,
    calculate_tdee,
)


def make_profile(**overrides) -> UserProfile:
    values = {
        "age": 30,
        "gender": Gender.MALE,
        "height_cm": 175,
        "weight_kg": 80,
        "activity_level": ActivityLevel.MODERATE,
        "goal": Goal.MAINTAIN,
    }
    return UserProfile(**(values | overrides))


def test_bmr_for_male():
    assert calculate_bmr(80, 175, 30, Gender.MALE) == pytest.approx(1748.75)


def test_bmr_for_female():
    assert calculate_bmr(60, 165, 25, Gender.FEMALE) == pytest.approx(1345.25)


def test_tdee_applies_activity_factor():
    assert calculate_tdee(make_profile()) == pytest.approx(1748.75 * 1.55)


@pytest.mark.parametrize(("goal", "adjustment"), [(Goal.LOSE, -500), (Goal.GAIN, 300)])
def test_goal_adjusts_calories(goal, adjustment):
    maintain = calculate_targets(make_profile()).calories
    assert calculate_targets(make_profile(goal=goal)).calories == maintain + adjustment


def test_calorie_floor_is_applied():
    profile = make_profile(
        gender=Gender.FEMALE,
        age=70,
        height_cm=150,
        weight_kg=42,
        activity_level=ActivityLevel.SEDENTARY,
        goal=Goal.LOSE,
    )
    assert calculate_targets(profile).calories == 1200


def test_macros_approximately_match_calories():
    targets = calculate_targets(make_profile())
    macro_calories = targets.protein_g * 4 + targets.carbs_g * 4 + targets.fat_g * 9
    assert macro_calories == pytest.approx(targets.calories, abs=10)


def test_invalid_profile_is_rejected():
    with pytest.raises(ValidationError):
        make_profile(age=5)
