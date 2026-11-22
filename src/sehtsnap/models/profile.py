"""User profile model."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class Gender(StrEnum):
    MALE = "male"
    FEMALE = "female"


class ActivityLevel(StrEnum):
    SEDENTARY = "sedentary"
    LIGHT = "light"
    MODERATE = "moderate"
    ACTIVE = "active"
    VERY_ACTIVE = "very_active"


class Goal(StrEnum):
    LOSE = "lose"
    MAINTAIN = "maintain"
    GAIN = "gain"


class HealthCondition(StrEnum):
    DIABETES = "diabetes"
    HYPERTENSION = "hypertension"
    CHOLESTEROL = "cholesterol"


class UserProfile(BaseModel):
    """Profile used for calorie targets and health advice."""

    name: str = Field(default="", max_length=80)
    age: int = Field(ge=13, le=100)
    gender: Gender
    height_cm: float = Field(gt=100, le=250)
    weight_kg: float = Field(gt=30, le=300)
    activity_level: ActivityLevel = ActivityLevel.SEDENTARY
    goal: Goal = Goal.MAINTAIN
    conditions: list[HealthCondition] = Field(default_factory=list)

    @field_validator("conditions")
    @classmethod
    def remove_duplicate_conditions(cls, value: list[HealthCondition]) -> list[HealthCondition]:
        return list(dict.fromkeys(value))
