"""Create a local demo account with 7 days of realistic meal logs."""

from __future__ import annotations

import sys
from dataclasses import replace
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from sehtsnap.core.config import load_settings  # noqa: E402
from sehtsnap.models import (  # noqa: E402
    ActivityLevel,
    Gender,
    Goal,
    HealthCondition,
    LogEntry,
    MealType,
    UserProfile,
)
from sehtsnap.services.auth_service import AuthError, LocalAuthService  # noqa: E402
from sehtsnap.services.db_service import SQLiteRepository  # noqa: E402
from sehtsnap.services.nutrition_db import NutritionDB  # noqa: E402

DEMO_EMAIL = "demo@sehtsnap.example"
DEMO_PASSWORD = "demo12345"
B, L, D, S = MealType.BREAKFAST, MealType.LUNCH, MealType.DINNER, MealType.SNACKS
WEEK_PLAN = [
    [(B, "anda_paratha", 1), (B, "doodh_patti", 1), (L, "daal_chawal", 1), (D, "chicken_karahi", 1), (D, "roti", 2), (S, "fruit_chaat", 1)],
    [(B, "omelette", 1), (B, "roti", 1), (L, "chicken_biryani", 1), (L, "raita", 1), (D, "daal_masoor", 1), (D, "roti", 2)],
    [(B, "halwa_puri", 1), (L, "aloo_gobi", 1), (L, "roti", 2), (D, "nihari", 1), (D, "naan", 1), (S, "doodh_patti", 1)],
    [(B, "plain_dahi", 1), (B, "boiled_egg", 2), (L, "chana_masala", 1), (L, "roti", 2), (D, "fish_curry", 1), (D, "plain_rice", 1)],
    [(B, "aloo_paratha", 1), (B, "doodh_patti", 1), (L, "chicken_pulao", 1), (D, "seekh_kebab", 1), (D, "naan", 1), (S, "samosa", 1)],
    [(B, "omelette", 1), (B, "roti", 1), (L, "sarson_saag", 1), (L, "roti", 2), (D, "chicken_tikka", 1), (D, "kachumber", 1)],
    [(B, "boiled_egg", 2), (B, "doodh_patti", 1), (L, "daal_moong", 1), (L, "plain_rice", 1), (S, "chana_chaat", 1)],
]  # fmt: skip


def main() -> None:
    settings = replace(load_settings(), force_demo=True)
    auth = LocalAuthService(settings.local_db_path)
    repository = SQLiteRepository(settings.local_db_path)
    nutrition = NutritionDB.from_json(settings.foods_path)
    try:
        user = auth.sign_up(DEMO_EMAIL, DEMO_PASSWORD)
    except AuthError:
        user = auth.sign_in(DEMO_EMAIL, DEMO_PASSWORD)

    repository.save_profile(
        user.uid,
        UserProfile(
            name="Ayesha Khan",
            age=34,
            gender=Gender.FEMALE,
            height_cm=163,
            weight_kg=70,
            activity_level=ActivityLevel.LIGHT,
            goal=Goal.LOSE,
            conditions=[HealthCondition.DIABETES],
        ),
    )
    repository.clear_user_data(user.uid)
    first_day = date.today() - timedelta(days=6)
    count = 0
    for offset, meals in enumerate(WEEK_PLAN):
        for meal, food_id, servings in meals:
            food = nutrition.get(food_id)
            if food is None:
                raise ValueError(f"Unknown demo food: {food_id}")
            repository.add_log(
                user.uid,
                LogEntry.from_food(food, meal, first_day + timedelta(days=offset), servings),
            )
            count += 1
    print(f"Seeded {count} meals into {settings.local_db_path}")
    print(f"Demo login: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    print("To use it while Firebase is configured, set DEMO_MODE=true in .env")


if __name__ == "__main__":
    main()
