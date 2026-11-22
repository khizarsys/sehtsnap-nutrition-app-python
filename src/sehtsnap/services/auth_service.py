"""Firebase Auth REST and local demo authentication behind one interface."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Protocol
from uuid import uuid4

import httpx

IDENTITY_URL = "https://identitytoolkit.googleapis.com/v1"
TOKEN_URL = "https://securetoken.googleapis.com/v1/token"
TOKEN_REFRESH_MARGIN_SECONDS = 60
MIN_PASSWORD_LENGTH = 8
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SCRYPT_PARAMS = {"n": 2**14, "r": 8, "p": 1, "dklen": 32}

FIREBASE_ERRORS = {
    "EMAIL_EXISTS": "An account with this email already exists.",
    "EMAIL_NOT_FOUND": "Incorrect email or password.",
    "INVALID_PASSWORD": "Incorrect email or password.",
    "INVALID_LOGIN_CREDENTIALS": "Incorrect email or password.",
    "INVALID_EMAIL": "Please enter a valid email address.",
    "USER_DISABLED": "This account has been disabled.",
    "TOO_MANY_ATTEMPTS_TRY_LATER": "Too many attempts. Please try again later.",
    "OPERATION_NOT_ALLOWED": "Email sign-in is not enabled for this project.",
}


class AuthError(Exception):
    """An authentication failure with a user-friendly message."""


@dataclass(frozen=True)
class AuthUser:
    uid: str
    email: str
    id_token: str = ""
    refresh_token: str = ""
    expires_at: float = 0.0


class AuthService(Protocol):
    def sign_up(self, email: str, password: str) -> AuthUser: ...

    def sign_in(self, email: str, password: str) -> AuthUser: ...

    def valid_user(self, user: AuthUser) -> AuthUser: ...


def validate_credentials(email: str, password: str) -> str:
    """Validate form input and return the normalized email."""
    normalized = email.strip().lower()
    if not EMAIL_PATTERN.match(normalized):
        raise AuthError("Please enter a valid email address.")
    if len(password) < MIN_PASSWORD_LENGTH:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
    return normalized


class FirebaseAuthService:
    """Firebase Identity Toolkit client."""

    def __init__(self, api_key: str, client: httpx.Client | None = None) -> None:
        self._api_key = api_key
        self._client = client or httpx.Client(timeout=15)

    def sign_up(self, email: str, password: str) -> AuthUser:
        return self._authenticate("signUp", email, password)

    def sign_in(self, email: str, password: str) -> AuthUser:
        return self._authenticate("signInWithPassword", email, password)

    def valid_user(self, user: AuthUser) -> AuthUser:
        """Return the user with a fresh ID token when the current one is expiring."""
        if time.time() < user.expires_at - TOKEN_REFRESH_MARGIN_SECONDS:
            return user
        data = self._post(
            TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": user.refresh_token},
        )
        return replace(
            user,
            id_token=data["id_token"],
            refresh_token=data["refresh_token"],
            expires_at=time.time() + int(data["expires_in"]),
        )

    def _authenticate(self, action: str, email: str, password: str) -> AuthUser:
        normalized = validate_credentials(email, password)
        data = self._post(
            f"{IDENTITY_URL}/accounts:{action}",
            json={"email": normalized, "password": password, "returnSecureToken": True},
        )
        return AuthUser(
            uid=data["localId"],
            email=data.get("email", normalized),
            id_token=data["idToken"],
            refresh_token=data["refreshToken"],
            expires_at=time.time() + int(data["expiresIn"]),
        )

    def _post(self, url: str, **kwargs) -> dict:
        try:
            response = self._client.post(url, headers={"x-goog-api-key": self._api_key}, **kwargs)
        except httpx.HTTPError as error:
            raise AuthError("Could not connect. Check your internet connection.") from error
        try:
            payload = response.json()
        except ValueError as error:
            raise AuthError("Sign-in is unavailable right now.") from error
        if response.is_success:
            return payload
        error_data = payload.get("error", {})
        code = str(error_data.get("message", "")) if isinstance(error_data, dict) else ""
        code = code.split(" ")[0].split(":")[0]
        if code.startswith("WEAK_PASSWORD"):
            raise AuthError(f"Password must be at least {MIN_PASSWORD_LENGTH} characters.")
        raise AuthError(FIREBASE_ERRORS.get(code, "Sign-in failed. Please try again."))


class LocalAuthService:
    """SQLite demo authentication with salted scrypt password hashes."""

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS users (
                    uid TEXT PRIMARY KEY,
                    email TEXT NOT NULL UNIQUE,
                    salt BLOB NOT NULL,
                    password_hash BLOB NOT NULL
                )"""
            )

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    @staticmethod
    def _hash(password: str, salt: bytes) -> bytes:
        return hashlib.scrypt(password.encode("utf-8"), salt=salt, **SCRYPT_PARAMS)

    def sign_up(self, email: str, password: str) -> AuthUser:
        normalized = validate_credentials(email, password)
        uid = uuid4().hex
        salt = secrets.token_bytes(16)
        try:
            with self._connect() as connection:
                connection.execute(
                    "INSERT INTO users (uid, email, salt, password_hash) VALUES (?, ?, ?, ?)",
                    (uid, normalized, salt, self._hash(password, salt)),
                )
        except sqlite3.IntegrityError as error:
            raise AuthError("An account with this email already exists.") from error
        return AuthUser(uid=uid, email=normalized)

    def sign_in(self, email: str, password: str) -> AuthUser:
        normalized = email.strip().lower()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT uid, salt, password_hash FROM users WHERE email = ?", (normalized,)
            ).fetchone()
        if row is None or not hmac.compare_digest(self._hash(password, row[1]), row[2]):
            raise AuthError("Incorrect email or password.")
        return AuthUser(uid=row[0], email=normalized)

    def valid_user(self, user: AuthUser) -> AuthUser:
        return user
