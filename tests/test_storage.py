import json
from datetime import date

import httpx
import pytest

from sehtsnap.models import FoodItem, Gender, HealthCondition, LogEntry, MealType, UserProfile
from sehtsnap.services.auth_service import AuthError, FirebaseAuthService, LocalAuthService
from sehtsnap.services.db_service import (
    DatabaseError,
    FirestoreRepository,
    SQLiteRepository,
    from_firestore_fields,
    to_firestore_fields,
)

FOOD = FoodItem(
    id="daal",
    name="Daal",
    calories=200,
    protein_g=12,
    carbs_g=30,
    fat_g=4,
    serving_size="1 bowl",
)
PROFILE = UserProfile(
    age=30,
    gender=Gender.FEMALE,
    height_cm=165,
    weight_kg=62,
    conditions=[HealthCondition.DIABETES],
)


def entry(day: int) -> LogEntry:
    return LogEntry.from_food(FOOD, MealType.LUNCH, date(2026, 1, day), 1.5)


def test_local_auth_flow(tmp_path):
    auth = LocalAuthService(tmp_path / "local.db")
    user = auth.sign_up("Test@Example.com", "password123")
    assert user.email == "test@example.com"
    assert auth.sign_in("test@example.com", "password123").uid == user.uid
    with pytest.raises(AuthError):
        auth.sign_in("test@example.com", "wrong-password")
    with pytest.raises(AuthError):
        auth.sign_up("test@example.com", "password123")


def test_local_auth_does_not_store_plain_password(tmp_path):
    path = tmp_path / "local.db"
    LocalAuthService(path).sign_up("a@example.com", "unique-password")
    assert b"unique-password" not in path.read_bytes()


def test_sqlite_repository_isolates_users(tmp_path):
    repository = SQLiteRepository(tmp_path / "local.db")
    repository.save_profile("a", PROFILE)
    repository.add_log("a", entry(2))
    repository.add_log("b", entry(2))
    assert repository.get_profile("a") == PROFILE
    assert repository.get_profile("b") is None
    assert len(repository.logs_between("a", date(2026, 1, 1), date(2026, 1, 3))) == 1
    repository.clear_user_data("a")
    assert repository.logs_between("a", date(2026, 1, 1), date(2026, 1, 3)) == []
    assert len(repository.logs_between("b", date(2026, 1, 1), date(2026, 1, 3))) == 1


def test_sqlite_date_range(tmp_path):
    repository = SQLiteRepository(tmp_path / "local.db")
    for day in (1, 2, 3):
        repository.add_log("a", entry(day))
    logs = repository.logs_between("a", date(2026, 1, 2), date(2026, 1, 3))
    assert [log.log_date.day for log in logs] == [2, 3]


def test_firestore_value_round_trip():
    data = {"a": 1, "b": 1.5, "c": True, "d": None, "e": ["x", 2], "f": {"g": "h"}, "i": []}
    assert from_firestore_fields(to_firestore_fields(data)) == data


def test_firebase_auth_maps_errors_without_leaking():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(400, json={"error": {"message": "INVALID_LOGIN_CREDENTIALS"}})

    service = FirebaseAuthService("key", httpx.Client(transport=httpx.MockTransport(handler)))
    with pytest.raises(AuthError, match="Incorrect email or password"):
        service.sign_in("a@example.com", "password123")


def test_firebase_auth_sends_key_in_header():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["url"] = str(request.url)
        seen["key"] = request.headers["x-goog-api-key"]
        return httpx.Response(
            200,
            json={
                "localId": "uid",
                "email": "a@example.com",
                "idToken": "id",
                "refreshToken": "refresh",
                "expiresIn": "3600",
            },
        )

    service = FirebaseAuthService("secret", httpx.Client(transport=httpx.MockTransport(handler)))
    assert service.sign_in("a@example.com", "password123").uid == "uid"
    assert seen["key"] == "secret"
    assert "secret" not in seen["url"]


def test_firestore_repository_uses_user_scoped_path_and_token():
    seen = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={})

    repository = FirestoreRepository(
        "demo", lambda: "token", httpx.Client(transport=httpx.MockTransport(handler))
    )
    log = entry(1)
    repository.add_log("user-1", log)
    assert f"/documents/users/user-1/logs/{log.id}" in seen[0].url.path
    assert seen[0].headers["authorization"] == "Bearer token"
    assert json.loads(seen[0].content)["fields"]["calories"] == {"doubleValue": 300.0}


def test_firestore_permission_error_is_friendly():
    repository = FirestoreRepository(
        "demo",
        lambda: "token",
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(403, json={}))),
    )
    with pytest.raises(DatabaseError, match="do not have permission"):
        repository.get_profile("user-1")


def test_firestore_expired_session_is_friendly():
    repository = FirestoreRepository(
        "demo",
        lambda: "token",
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(401, json={}))),
    )
    with pytest.raises(DatabaseError, match="sign in again"):
        repository.get_profile("user-1")
