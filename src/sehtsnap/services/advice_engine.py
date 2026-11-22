"""Rule-based dietary guidance from health conditions and dish tags.

This module provides general wellness information and is not medical advice.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum

from sehtsnap.models.food import FoodItem
from sehtsnap.models.profile import HealthCondition


class Severity(StrEnum):
    CAUTION = "caution"
    LIMIT = "limit"


@dataclass(frozen=True)
class AdviceRule:
    condition: HealthCondition
    tag: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class Warning:
    condition: HealthCondition
    tag: str
    severity: Severity
    message: str


@dataclass(frozen=True)
class Advice:
    warnings: list[Warning] = field(default_factory=list)
    alternatives: list[FoodItem] = field(default_factory=list)

    @property
    def is_clear(self) -> bool:
        return not self.warnings


RULES: tuple[AdviceRule, ...] = (
    AdviceRule(
        HealthCondition.DIABETES,
        "high_sugar",
        Severity.LIMIT,
        "High sugar: limit this if you have diabetes.",
    ),
    AdviceRule(
        HealthCondition.DIABETES,
        "refined_carb",
        Severity.LIMIT,
        "Refined carbs can raise blood sugar quickly.",
    ),
    AdviceRule(
        HealthCondition.DIABETES,
        "high_carb",
        Severity.CAUTION,
        "High in carbs: keep the portion small and add salad or protein.",
    ),
    AdviceRule(
        HealthCondition.DIABETES,
        "natural_sugar",
        Severity.CAUTION,
        "Contains natural sugars: watch the portion size.",
    ),
    AdviceRule(
        HealthCondition.HYPERTENSION,
        "high_salt",
        Severity.LIMIT,
        "High salt: limit this if you have high blood pressure.",
    ),
    AdviceRule(
        HealthCondition.HYPERTENSION,
        "fried",
        Severity.CAUTION,
        "Fried foods are often salty and are best eaten occasionally.",
    ),
    AdviceRule(
        HealthCondition.CHOLESTEROL,
        "fried",
        Severity.LIMIT,
        "Fried food: limit this if you have high cholesterol.",
    ),
    AdviceRule(
        HealthCondition.CHOLESTEROL,
        "high_fat",
        Severity.LIMIT,
        "High fat: choose a smaller portion or a leaner option.",
    ),
    AdviceRule(
        HealthCondition.CHOLESTEROL,
        "red_meat",
        Severity.CAUTION,
        "Red meat can be high in saturated fat: choose lean cuts.",
    ),
)
SEVERITY_ORDER = {Severity.LIMIT: 0, Severity.CAUTION: 1}
PREFERRED_TAGS = {"high_fiber", "lean_protein", "low_fat", "grilled"}


def get_warnings(food: FoodItem, conditions: list[HealthCondition]) -> list[Warning]:
    """Return warnings for a food, most severe first."""
    active = set(conditions)
    tags = set(food.tags)
    warnings = [
        Warning(rule.condition, rule.tag, rule.severity, rule.message)
        for rule in RULES
        if rule.condition in active and rule.tag in tags
    ]
    return sorted(warnings, key=lambda warning: SEVERITY_ORDER[warning.severity])


def find_alternatives(
    food: FoodItem,
    foods: list[FoodItem],
    conditions: list[HealthCondition],
    limit: int = 3,
) -> list[FoodItem]:
    """Return lower-calorie foods with no warnings, closest in type first."""
    candidates = [
        candidate
        for candidate in foods
        if candidate.id != food.id
        and candidate.calories < food.calories
        and candidate.calories >= 90
        and not get_warnings(candidate, conditions)
    ]

    def rank(candidate: FoodItem) -> tuple[int, int, float, str]:
        same_diet = ("vegetarian" in candidate.tags) == ("vegetarian" in food.tags)
        healthy_tags = len(PREFERRED_TAGS & set(candidate.tags))
        return (not same_diet, -healthy_tags, abs(food.calories - candidate.calories), candidate.id)

    return sorted(candidates, key=rank)[:limit]


def get_advice(food: FoodItem, foods: list[FoodItem], conditions: list[HealthCondition]) -> Advice:
    """Return warnings and, when needed, healthier alternatives."""
    warnings = get_warnings(food, conditions)
    alternatives = find_alternatives(food, foods, conditions) if warnings else []
    return Advice(warnings=warnings, alternatives=alternatives)
