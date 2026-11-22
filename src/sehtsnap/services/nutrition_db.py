"""Load, search and fuzzy-match the local South Asian nutrition dataset."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from rapidfuzz import fuzz, process

from sehtsnap.models.food import FoodItem

MATCH_THRESHOLD = 82.0


@dataclass(frozen=True)
class FoodMatch:
    """A dataset food and its 0-100 similarity score."""

    food: FoodItem
    score: float


def normalize(text: str) -> str:
    """Lowercase text and collapse whitespace for comparison."""
    return " ".join(text.casefold().replace("-", " ").split())


class NutritionDB:
    """In-memory, read-only food repository."""

    def __init__(self, foods: list[FoodItem]) -> None:
        ids = [food.id for food in foods]
        if len(ids) != len(set(ids)):
            raise ValueError("Food ids must be unique")
        self.foods = foods
        self._by_id = {food.id: food for food in foods}
        self._terms: list[tuple[str, FoodItem]] = [
            (normalize(term), food) for food in foods for term in (food.name, *food.aliases)
        ]
        self._choices = [term for term, _ in self._terms]

    @classmethod
    def from_json(cls, path: Path) -> NutritionDB:
        """Build a repository from a JSON dataset file."""
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls([FoodItem.model_validate(item) for item in raw])

    def get(self, food_id: str) -> FoodItem | None:
        return self._by_id.get(food_id)

    def suggestions(self, query: str, limit: int = 3) -> list[FoodMatch]:
        """Return the best distinct foods for a query, highest score first."""
        needle = normalize(query)
        if not needle or limit <= 0:
            return []
        results = process.extract(
            needle, self._choices, scorer=fuzz.WRatio, limit=max(limit * 6, 20)
        )
        best: dict[str, FoodMatch] = {}
        for term, score, index in results:
            food = self._terms[index][1]
            adjusted = 100.0 if term == needle else float(score)
            if food.id not in best or adjusted > best[food.id].score:
                best[food.id] = FoodMatch(food, adjusted)
        return sorted(best.values(), key=lambda match: match.score, reverse=True)[:limit]

    def match(self, dish: str, threshold: float = MATCH_THRESHOLD) -> FoodMatch | None:
        """Return the best match if it meets the threshold."""
        matches = self.suggestions(dish, limit=1)
        return matches[0] if matches and matches[0].score >= threshold else None

    def search(self, query: str, limit: int = 20) -> list[FoodItem]:
        """Search foods, preferring direct text matches over fuzzy matches."""
        needle = normalize(query)
        if not needle:
            return self.foods[:limit]
        direct: dict[str, FoodItem] = {}
        for term, food in self._terms:
            if needle in term:
                direct.setdefault(food.id, food)
        results = list(direct.values())
        if len(results) < limit:
            for item in self.suggestions(needle, limit=limit):
                if item.score >= 70 and item.food.id not in direct:
                    results.append(item.food)
        return results[:limit]
