"""Nutrition dataset model."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FoodItem(BaseModel):
    """A dish with nutrition values for one standard serving."""

    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    aliases: list[str] = Field(default_factory=list)
    calories: float = Field(ge=0)
    protein_g: float = Field(ge=0)
    carbs_g: float = Field(ge=0)
    fat_g: float = Field(ge=0)
    serving_size: str = Field(min_length=1)
    tags: list[str] = Field(default_factory=list)
