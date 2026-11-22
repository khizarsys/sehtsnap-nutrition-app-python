"""Identify dishes from photos with Gemini or OpenAI vision models."""

from __future__ import annotations

import base64
import io
import json
import logging
import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol
from urllib.parse import urlsplit

import httpx
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import ValidationError

from sehtsnap.core.config import Settings
from sehtsnap.models.detection import DetectionResult

logger = logging.getLogger(__name__)

LOW_CONFIDENCE_THRESHOLD = 0.6
MAX_IMAGE_SIDE = 1024
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
REQUEST_TIMEOUT_SECONDS = 30

DETECTION_PROMPT = """You identify South Asian food from photos.
Return only one JSON object with exactly these keys:
{"dish": string, "confidence": number, "serving_estimate": number}

Rules:
- dish: the most specific common dish name, such as "Chicken Biryani" or "Daal Chawal".
- confidence: a number from 0 to 1.
- serving_estimate: visible standard servings, from 0.25 to 10.
- If the image does not show food, use {"dish": "unknown", "confidence": 0,
  "serving_estimate": 1}.
- Do not include markdown or explanations."""

MISSING_KEY_MESSAGE = "AI detection is not set up. You can search for your dish manually."
INVALID_IMAGE_MESSAGE = "That image could not be read. Please try another photo."
BAD_RESPONSE_MESSAGE = "The dish could not be identified. Please search for it manually."
SERVICE_ERROR_MESSAGE = "AI detection is unavailable right now. Please search manually."
SIGN_IN_MESSAGE = "Please sign in again to use AI detection."
LIMIT_MESSAGE = "AI detection limit reached. Please try later or search manually."
BACKEND_TIMEOUT_SECONDS = 75
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


class AIResponseError(ValueError):
    """Raised when a provider response does not satisfy the JSON contract."""


class AIServiceError(Exception):
    """A provider failure with a message that is safe to show users."""


class VisionProvider(Protocol):
    """A provider that returns raw JSON text for a JPEG image."""

    def generate(self, jpeg_bytes: bytes) -> str: ...


@dataclass(frozen=True)
class DetectionOutcome:
    """A safe result for the UI: either a detection or a friendly error."""

    result: DetectionResult | None = None
    error: str | None = None

    @property
    def needs_review(self) -> bool:
        return (
            self.result is None
            or self.result.confidence < LOW_CONFIDENCE_THRESHOLD
            or self.result.dish.casefold() == "unknown"
        )


def parse_detection(raw: str) -> DetectionResult:
    """Parse and validate strict JSON, tolerating a surrounding code fence."""
    text = (raw or "").strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    if fenced:
        text = fenced.group(1)
    try:
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise AIResponseError("Response must be a JSON object")
        return DetectionResult.model_validate(payload)
    except (json.JSONDecodeError, ValidationError) as error:
        raise AIResponseError("Invalid detection response") from error


def prepare_image(image_bytes: bytes) -> bytes:
    """Validate, orient, resize and compress an image to JPEG."""
    if not image_bytes or len(image_bytes) > MAX_UPLOAD_BYTES:
        raise ValueError("Image is empty or too large")
    try:
        with Image.open(io.BytesIO(image_bytes)) as source:
            image = ImageOps.exif_transpose(source).convert("RGB")
            image.thumbnail((MAX_IMAGE_SIDE, MAX_IMAGE_SIDE), Image.Resampling.LANCZOS)
            output = io.BytesIO()
            image.save(output, format="JPEG", quality=82, optimize=True)
            return output.getvalue()
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("Unreadable image") from error


class GeminiProvider:
    """Google Gemini vision provider."""

    def __init__(self, api_key: str, model: str) -> None:
        from google import genai
        from google.genai import types

        self._types = types
        self._model = model
        self._client = genai.Client(
            api_key=api_key,
            http_options=types.HttpOptions(
                timeout=REQUEST_TIMEOUT_SECONDS * 1000,
                retry_options=types.HttpRetryOptions(
                    attempts=2,
                    initial_delay=1.0,
                    http_status_codes=[429, 500, 502, 503, 504],
                ),
            ),
        )

    def generate(self, jpeg_bytes: bytes) -> str:
        response = self._client.models.generate_content(
            model=self._model,
            contents=[
                self._types.Part.from_bytes(data=jpeg_bytes, mime_type="image/jpeg"),
                DETECTION_PROMPT,
            ],
            config=self._types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return response.text or ""


class OpenAIProvider:
    """OpenAI vision provider."""

    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self._model = model
        self._client = OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS, max_retries=1)

    def generate(self, jpeg_bytes: bytes) -> str:
        encoded = base64.b64encode(jpeg_bytes).decode("ascii")
        response = self._client.chat.completions.create(
            model=self._model,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": DETECTION_PROMPT},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{encoded}"},
                        },
                    ],
                }
            ],
        )
        return response.choices[0].message.content or ""


class BackendProvider:
    """Send photos to the SehtSnap API so mobile apps never hold an AI key."""

    def __init__(
        self,
        base_url: str,
        token_provider: Callable[[], str],
        client: httpx.Client | None = None,
    ) -> None:
        parts = urlsplit(base_url)
        secure = parts.scheme == "https" and bool(parts.hostname)
        local = parts.scheme == "http" and parts.hostname in LOCAL_HOSTS
        if not (secure or local):
            raise ValueError("AI backend URL must use https")
        self._url = f"{base_url.rstrip('/')}/v1/detect"
        self._token_provider = token_provider
        self._client = client or httpx.Client(timeout=BACKEND_TIMEOUT_SECONDS)

    def generate(self, jpeg_bytes: bytes) -> str:
        token = self._token_provider()
        if not token:
            raise AIServiceError(SIGN_IN_MESSAGE)
        try:
            response = self._client.post(
                self._url,
                content=jpeg_bytes,
                headers={"Authorization": f"Bearer {token}", "Content-Type": "image/jpeg"},
            )
        except httpx.HTTPError as error:
            raise AIServiceError(SERVICE_ERROR_MESSAGE) from error
        if response.status_code == 401:
            raise AIServiceError(SIGN_IN_MESSAGE)
        if response.status_code == 429:
            raise AIServiceError(LIMIT_MESSAGE)
        if response.status_code in (413, 415, 422):
            raise AIServiceError(INVALID_IMAGE_MESSAGE)
        if response.status_code == 502:
            raise AIResponseError("Invalid backend response")
        if response.status_code != 200:
            raise AIServiceError(SERVICE_ERROR_MESSAGE)
        return response.text


def create_provider(
    settings: Settings,
    provider_name: str | None = None,
    token_provider: Callable[[], str] | None = None,
) -> VisionProvider | None:
    """Create the configured provider, preferring the secure backend."""
    if settings.ai_backend_url and token_provider and not settings.demo_mode:
        return BackendProvider(settings.ai_backend_url, token_provider)
    name = provider_name or settings.ai_provider
    if name == "openai":
        if not settings.openai_api_key:
            return None
        return OpenAIProvider(settings.openai_api_key, settings.openai_model)
    if not settings.gemini_api_key:
        return None
    return GeminiProvider(settings.gemini_api_key, settings.gemini_model)


class AIVisionService:
    """Detect dishes and convert every failure into a friendly outcome."""

    def __init__(self, provider: VisionProvider | None) -> None:
        self._provider = provider

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        provider_name: str | None = None,
        token_provider: Callable[[], str] | None = None,
    ) -> AIVisionService:
        try:
            return cls(create_provider(settings, provider_name, token_provider))
        except Exception as error:
            logger.warning("Could not initialize AI provider: %s", type(error).__name__)
            return cls(None)

    def detect(self, image_bytes: bytes) -> DetectionOutcome:
        if self._provider is None:
            return DetectionOutcome(error=MISSING_KEY_MESSAGE)
        try:
            jpeg = prepare_image(image_bytes)
        except ValueError:
            return DetectionOutcome(error=INVALID_IMAGE_MESSAGE)
        try:
            return DetectionOutcome(result=parse_detection(self._provider.generate(jpeg)))
        except AIResponseError:
            return DetectionOutcome(error=BAD_RESPONSE_MESSAGE)
        except AIServiceError as error:
            return DetectionOutcome(error=str(error))
        except Exception as error:
            # Log only the type so provider errors cannot expose request details.
            logger.warning("AI detection failed: %s", type(error).__name__)
            return DetectionOutcome(error=SERVICE_ERROR_MESSAGE)
