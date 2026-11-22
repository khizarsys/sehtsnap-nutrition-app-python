"""Daily calorie and macro targets using the Mifflin-St Jeor equation."""

from __future__ import annotations

from dataclasses import dataclass

from sehtsnap.models.profile import ActivityLevel, Gender, Goal, UserProfile

ACTIVITY_FACTORS: dict[ActivityLevel, float] = {
    ActivityLevel.SEDENTARY: 1.2,
    ActivityLevel.LIGHT: 1.375,
    ActivityLevel.MODERATE: 1.55,
    ActivityLevel.ACTIVE: 1.725,
    ActivityLevel.VERY_ACTIVE: 1.9,
}
GOAL_ADJUSTMENTS: dict[Goal, int] = {Goal.LOSE: -500, Goal.MAINTAIN: 0, Goal.GAIN: 300}
MINIMUM_CALORIES: dict[Gender, int] = {Gender.FEMALE: 1200, Gender.MALE: 1500}
MACRO_SPLITS: dict[Goal, tuple[float, float, float]] = {
    Goal.LOSE: (0.30, 0.40, 0.30),
    Goal.MAINTAIN: (0.20, 0.50, 0.30),
    Goal.GAIN: (0.25, 0.50, 0.25),
}
CALORIES_PER_GRAM = {"protein": 4, "carbs": 4, "fat": 9}


@dataclass(frozen=True)
class DailyTargets:
    """Daily nutrition targets."""

    calories: int
    protein_g: int
    carbs_g: int
    fat_g: int


def calculate_bmr(weight_kg: float, height_cm: float, age: int, gender: Gender) -> float:
    """Return basal metabolic rate in kcal/day."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if gender == Gender.MALE else base - 161


def calculate_tdee(profile: UserProfile) -> float:
    """Return total daily energy expenditure in kcal/day."""
    bmr = calculate_bmr(profile.weight_kg, profile.height_cm, profile.age, profile.gender)
    return bmr * ACTIVITY_FACTORS[profile.activity_level]


def calculate_targets(profile: UserProfile) -> DailyTargets:
    """Return calorie and macro targets, respecting a safe calorie floor."""
    adjusted = calculate_tdee(profile) + GOAL_ADJUSTMENTS[profile.goal]
    calories = round(max(adjusted, MINIMUM_CALORIES[profile.gender]))
    protein_share, carbs_share, fat_share = MACRO_SPLITS[profile.goal]
    return DailyTargets(
        calories=calories,
        protein_g=round(calories * protein_share / CALORIES_PER_GRAM["protein"]),
        carbs_g=round(calories * carbs_share / CALORIES_PER_GRAM["carbs"]),
        fat_g=round(calories * fat_share / CALORIES_PER_GRAM["fat"]),
    )
