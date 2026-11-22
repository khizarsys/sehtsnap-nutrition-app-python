"""Observable application state, independent of the UI toolkit."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sehtsnap.core.config import Settings
from sehtsnap.models import FoodItem, LogEntry, MealType, UserProfile
from sehtsnap.services.advice_engine import Advice, get_advice
from sehtsnap.services.ai_vision_service import AIVisionService, DetectionOutcome
from sehtsnap.services.auth_service import (
    AuthService,
    AuthUser,
    FirebaseAuthService,
    LocalAuthService,
)
from sehtsnap.services.calorie_calculator import DailyTargets, calculate_targets
from sehtsnap.services.db_service import FirestoreRepository, Repository, SQLiteRepository
from sehtsnap.services.nutrition_db import NutritionDB


@dataclass(frozen=True)
class Totals:
    calories: float = 0
    protein_g: float = 0
    carbs_g: float = 0
    fat_g: float = 0


def sum_entries(entries: list[LogEntry]) -> Totals:
    """Add nutrition values across log entries."""
    return Totals(
        calories=round(sum(entry.calories for entry in entries), 1),
        protein_g=round(sum(entry.protein_g for entry in entries), 1),
        carbs_g=round(sum(entry.carbs_g for entry in entries), 1),
        fat_g=round(sum(entry.fat_g for entry in entries), 1),
    )


def default_meal(now: datetime | None = None) -> MealType:
    """Suggest a meal from the local time."""
    hour = (now or datetime.now()).hour
    if 5 <= hour < 11:
        return MealType.BREAKFAST
    if 11 <= hour < 16:
        return MealType.LUNCH
    if 18 <= hour < 23:
        return MealType.DINNER
    return MealType.SNACKS


class AppState:
    """Single source of truth for the signed-in session."""

    def __init__(
        self,
        settings: Settings,
        nutrition: NutritionDB,
        auth: AuthService | None = None,
        repository: Repository | None = None,
    ) -> None:
        self.settings = settings
        self.nutrition = nutrition
        self.user: AuthUser | None = None
        self.profile: UserProfile | None = None
        self.selected_date = date.today()
        self.ai_provider = settings.ai_provider
        self.units = "metric"
        self.pending_servings = 1.0
        self.pending_photo: bytes | None = None
        self._listeners: list[Callable[[], None]] = []
        if settings.demo_mode:
            self.auth = auth or LocalAuthService(settings.local_db_path)
            self.repository = repository or SQLiteRepository(settings.local_db_path)
        else:
            self.auth = auth or FirebaseAuthService(settings.firebase_api_key)
            self.repository = repository or FirestoreRepository(
                settings.firebase_project_id, self._id_token
            )

    def subscribe(self, listener: Callable[[], None]) -> None:
        self._listeners.append(listener)

    def notify(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _id_token(self) -> str:
        if self.user is None:
            return ""
        self.user = self.auth.valid_user(self.user)
        return self.user.id_token

    @property
    def uid(self) -> str:
        if self.user is None:
            raise RuntimeError("No signed-in user")
        return self.user.uid

    @property
    def targets(self) -> DailyTargets | None:
        return calculate_targets(self.profile) if self.profile else None

    def sign_in(self, email: str, password: str) -> None:
        self._start_session(self.auth.sign_in(email, password))

    def sign_up(self, email: str, password: str) -> None:
        self._start_session(self.auth.sign_up(email, password))

    def _start_session(self, user: AuthUser) -> None:
        self.user = user
        try:
            self.profile = self.repository.get_profile(user.uid)
        except Exception:
            self.user = None
            self.profile = None
            raise
        self.selected_date = date.today()
        self.notify()

    def sign_out(self) -> None:
        self.user = None
        self.profile = None
        self.pending_servings = 1.0
        self.pending_photo = None
        self.notify()

    def save_profile(self, profile: UserProfile) -> None:
        self.repository.save_profile(self.uid, profile)
        self.profile = profile
        self.notify()

    def logs_for(self, day: date) -> list[LogEntry]:
        return self.repository.logs_between(self.uid, day, day)

    def add_food(self, food: FoodItem, meal: MealType, servings: float, day: date) -> LogEntry:
        entry = LogEntry.from_food(food, meal, day, servings)
        self.repository.add_log(self.uid, entry)
        self.notify()
        return entry

    def remove_entry(self, entry_id: str) -> None:
        self.repository.delete_log(self.uid, entry_id)
        self.notify()

    def reset_logs(self) -> None:
        self.repository.clear_user_data(self.uid)
        self.notify()

    def weekly_calories(self, end: date | None = None) -> list[tuple[date, float]]:
        """Return calories for each of the 7 days ending on `end`."""
        last = end or date.today()
        first = last - timedelta(days=6)
        totals = {first + timedelta(days=index): 0.0 for index in range(7)}
        for entry in self.repository.logs_between(self.uid, first, last):
            totals[entry.log_date] += entry.calories
        return [(day, round(value, 1)) for day, value in totals.items()]

    def detect(self, image_bytes: bytes) -> DetectionOutcome:
        service = AIVisionService.from_settings(self.settings, self.ai_provider, self._id_token)
        return service.detect(image_bytes)

    def advice_for(self, food: FoodItem) -> Advice:
        conditions = self.profile.conditions if self.profile else []
        return get_advice(food, self.nutrition.foods, conditions)
