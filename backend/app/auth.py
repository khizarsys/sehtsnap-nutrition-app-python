"""Firebase ID token verification."""

from __future__ import annotations

from typing import Protocol

import cachecontrol
import google.auth.exceptions
import google.auth.transport.requests
import requests
from google.oauth2 import id_token


class InvalidTokenError(Exception):
    """The caller did not present a valid Firebase ID token."""


class TokenVerifier(Protocol):
    def verify(self, token: str) -> str: ...


class FirebaseTokenVerifier:
    """Verify Firebase tokens with Google's public certificates."""

    def __init__(self, project_id: str) -> None:
        self._project_id = project_id
        self._issuer = f"https://securetoken.google.com/{project_id}"
        session = cachecontrol.CacheControl(requests.Session())
        self._request = google.auth.transport.requests.Request(session=session)

    def verify(self, token: str) -> str:
        """Return the Firebase user ID for a valid token."""
        try:
            claims = id_token.verify_firebase_token(token, self._request, audience=self._project_id)
        except google.auth.exceptions.TransportError:
            raise
        except (ValueError, google.auth.exceptions.GoogleAuthError) as error:
            raise InvalidTokenError from error
        uid = claims.get("sub") if claims else None
        if not uid or claims.get("iss") != self._issuer:
            raise InvalidTokenError
        return str(uid)
