"""Food log model."""

from __future__ import annotations

from datetime import date
from enum import StrEnum
from uuid import uuid4

from pydantic import BaseModel, Field

from sehtsnap.models.food import FoodItem


class MealType(StrEnum):
    BREAKFAST = "breakfast"
    LUNCH = "lunch"
    DINNER = "dinner"
    SNACKS = "snacks"


class LogEntry(BaseModel):
    """A logged food with nutrition values frozen at logging time."""

    id: str = Field(default_factory=lambda: uuid4().hex)
    food_id: str
    food_name: str
    meal: MealType
    log_date: date
    servings: float = Field(gt=0, le=10)
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)

    @classmethod
    def from_food(
        cls, food: FoodItem, meal: MealType, log_date: date, servings: float = 1.0
    ) -> LogEntry:
        """Create an entry by scaling a food's values to the chosen servings."""
        return cls(
            food_id=food.id,
            food_name=food.name,
            meal=meal,
            log_date=log_date,
            servings=servings,
            calories=round(food.calories * servings, 1),
            protein_g=round(food.protein_g * servings, 1),
            carbs_g=round(food.carbs_g * servings, 1),
            fat_g=round(food.fat_g * servings, 1),
        )
