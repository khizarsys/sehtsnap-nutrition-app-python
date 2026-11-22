"""Firestore REST and SQLite repositories with the same interface."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Callable
from datetime import date
from pathlib import Path
from typing import Any, Protocol
from urllib.parse import quote

import httpx
from pydantic import ValidationError

from sehtsnap.models.log import LogEntry
from sehtsnap.models.profile import UserProfile

FIRESTORE_URL = "https://firestore.googleapis.com/v1"


class DatabaseError(Exception):
    """A storage failure with a user-friendly message."""


class Repository(Protocol):
    def get_profile(self, uid: str) -> UserProfile | None: ...

    def save_profile(self, uid: str, profile: UserProfile) -> None: ...

    def add_log(self, uid: str, entry: LogEntry) -> None: ...

    def delete_log(self, uid: str, entry_id: str) -> None: ...

    def logs_between(self, uid: str, start: date, end: date) -> list[LogEntry]: ...

    def clear_user_data(self, uid: str) -> None: ...


def to_firestore_value(value: Any) -> dict[str, Any]:
    """Encode a JSON-compatible Python value as a Firestore value."""
    if value is None:
        return {"nullValue": None}
    if isinstance(value, bool):
        return {"booleanValue": value}
    if isinstance(value, int):
        return {"integerValue": str(value)}
    if isinstance(value, float):
        return {"doubleValue": value}
    if isinstance(value, str):
        return {"stringValue": value}
    if isinstance(value, list):
        return {"arrayValue": {"values": [to_firestore_value(item) for item in value]}}
    if isinstance(value, dict):
        return {"mapValue": {"fields": to_firestore_fields(value)}}
    raise TypeError(f"Unsupported Firestore value: {type(value).__name__}")


def to_firestore_fields(data: dict[str, Any]) -> dict[str, Any]:
    return {key: to_firestore_value(value) for key, value in data.items()}


def from_firestore_value(value: dict[str, Any]) -> Any:
    """Decode a Firestore value into a Python value."""
    kind, content = next(iter(value.items()))
    if kind == "integerValue":
        return int(content)
    if kind == "arrayValue":
        return [from_firestore_value(item) for item in content.get("values", [])]
    if kind == "mapValue":
        return from_firestore_fields(content.get("fields", {}))
    if kind == "nullValue":
        return None
    return content


def from_firestore_fields(fields: dict[str, Any]) -> dict[str, Any]:
    return {key: from_firestore_value(value) for key, value in fields.items()}


class FirestoreRepository:
    """Per-user storage at `users/{uid}` and `users/{uid}/logs/{entry}`."""

    def __init__(
        self,
        project_id: str,
        token_provider: Callable[[], str],
        client: httpx.Client | None = None,
    ) -> None:
        self._token_provider = token_provider
        self._client = client or httpx.Client(timeout=15)
        self._database = f"projects/{quote(project_id, safe='')}/databases/(default)/documents"

    def _user_path(self, uid: str) -> str:
        return f"{self._database}/users/{quote(uid, safe='')}"

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        try:
            headers = {"Authorization": f"Bearer {self._token_provider()}"}
            response = self._client.request(
                method, f"{FIRESTORE_URL}/{path}", headers=headers, **kwargs
            )
        except httpx.HTTPError as error:
            raise DatabaseError("Could not connect. Check your internet connection.") from error
        if response.status_code == 401:
            raise DatabaseError("Your session has expired. Please sign in again.")
        if response.status_code == 403:
            raise DatabaseError("You do not have permission to access this data.")
        if response.is_error and response.status_code != 404:
            raise DatabaseError("Your data could not be saved or loaded. Please try again.")
        return response

    def get_profile(self, uid: str) -> UserProfile | None:
        response = self._request("GET", self._user_path(uid))
        if response.status_code == 404:
            return None
        profile = from_firestore_fields(response.json().get("fields", {})).get("profile")
        if profile is None:
            return None
        try:
            return UserProfile.model_validate(profile)
        except ValidationError as error:
            raise DatabaseError("Your saved profile could not be read.") from error

    def save_profile(self, uid: str, profile: UserProfile) -> None:
        body = {"fields": to_firestore_fields({"profile": profile.model_dump(mode="json")})}
        self._request(
            "PATCH",
            self._user_path(uid),
            params={"updateMask.fieldPaths": "profile"},
            json=body,
        )

    def add_log(self, uid: str, entry: LogEntry) -> None:
        path = f"{self._user_path(uid)}/logs/{quote(entry.id, safe='')}"
        self._request("PATCH", path, json={"fields": to_firestore_fields(self._log_data(entry))})

    def delete_log(self, uid: str, entry_id: str) -> None:
        self._request("DELETE", f"{self._user_path(uid)}/logs/{quote(entry_id, safe='')}")

    def logs_between(self, uid: str, start: date, end: date) -> list[LogEntry]:
        query = {
            "structuredQuery": {
                "from": [{"collectionId": "logs"}],
                "where": {
                    "compositeFilter": {
                        "op": "AND",
                        "filters": [
                            self._date_filter("GREATER_THAN_OR_EQUAL", start),
                            self._date_filter("LESS_THAN_OR_EQUAL", end),
                        ],
                    }
                },
            }
        }
        response = self._request("POST", f"{self._user_path(uid)}:runQuery", json=query)
        if response.status_code == 404:
            return []
        entries = []
        for row in response.json():
            document = row.get("document")
            if document:
                entries.append(LogEntry.model_validate(from_firestore_fields(document["fields"])))
        return sorted(entries, key=lambda entry: (entry.log_date, entry.meal.value, entry.id))

    def clear_user_data(self, uid: str) -> None:
        for entry in self.logs_between(uid, date.min, date.max):
            self.delete_log(uid, entry.id)

    @staticmethod
    def _log_data(entry: LogEntry) -> dict[str, Any]:
        data = entry.model_dump(mode="json")
        for key in ("servings", "calories", "protein_g", "carbs_g", "fat_g"):
            data[key] = float(data[key])
        return data

    @staticmethod
    def _date_filter(operator: str, value: date) -> dict[str, Any]:
        return {
            "fieldFilter": {
                "field": {"fieldPath": "log_date"},
                "op": operator,
                "value": {"stringValue": value.isoformat()},
            }
        }


class SQLiteRepository:
    """Local demo-mode repository."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS profiles (uid TEXT PRIMARY KEY, data TEXT NOT NULL)"
            )
            connection.execute(
                """CREATE TABLE IF NOT EXISTS logs (
                    id TEXT NOT NULL,
                    uid TEXT NOT NULL,
                    log_date TEXT NOT NULL,
                    data TEXT NOT NULL,
                    PRIMARY KEY (uid, id)
                )"""
            )
            connection.execute("CREATE INDEX IF NOT EXISTS idx_logs ON logs (uid, log_date)")

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def get_profile(self, uid: str) -> UserProfile | None:
        with self._connect() as connection:
            row = connection.execute("SELECT data FROM profiles WHERE uid = ?", (uid,)).fetchone()
        return UserProfile.model_validate(json.loads(row[0])) if row else None

    def save_profile(self, uid: str, profile: UserProfile) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO profiles (uid, data) VALUES (?, ?)",
                (uid, profile.model_dump_json()),
            )

    def add_log(self, uid: str, entry: LogEntry) -> None:
        with self._connect() as connection:
            connection.execute(
                "INSERT OR REPLACE INTO logs (id, uid, log_date, data) VALUES (?, ?, ?, ?)",
                (entry.id, uid, entry.log_date.isoformat(), entry.model_dump_json()),
            )

    def delete_log(self, uid: str, entry_id: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM logs WHERE uid = ? AND id = ?", (uid, entry_id))

    def logs_between(self, uid: str, start: date, end: date) -> list[LogEntry]:
        with self._connect() as connection:
            rows = connection.execute(
                """SELECT data FROM logs
                   WHERE uid = ? AND log_date BETWEEN ? AND ?
                   ORDER BY log_date, id""",
                (uid, start.isoformat(), end.isoformat()),
            ).fetchall()
        return [LogEntry.model_validate_json(row[0]) for row in rows]

    def clear_user_data(self, uid: str) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM logs WHERE uid = ?", (uid,))
