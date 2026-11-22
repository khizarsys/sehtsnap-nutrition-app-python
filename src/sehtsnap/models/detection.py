"""AI detection result model."""

from __future__ import annotations

from pydantic import BaseModel, Field, field_validator


class DetectionResult(BaseModel):
    """Strict JSON contract returned by the AI vision provider."""

    dish: str = Field(min_length=1, max_length=120)
    confidence: float = Field(ge=0, le=1)
    serving_estimate: float = Field(default=1.0, gt=0, le=10)

    @field_validator("dish")
    @classmethod
    def normalize_dish(cls, value: str) -> str:
        cleaned = " ".join(value.split())
        if not cleaned:
            raise ValueError("dish must not be blank")
        return cleaned
