"""SehtSnap food detection API."""

from __future__ import annotations

import io
import logging
from collections.abc import Callable

from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.concurrency import run_in_threadpool
from PIL import Image, UnidentifiedImageError

from backend.app.auth import FirebaseTokenVerifier, InvalidTokenError, TokenVerifier
from backend.app.config import BackendSettings, load_backend_settings
from backend.app.rate_limit import RateLimiter
from sehtsnap.models.detection import DetectionResult
from sehtsnap.services.ai_vision_service import (
    AIResponseError,
    GeminiProvider,
    parse_detection,
    prepare_image,
)

logger = logging.getLogger(__name__)
MAX_IMAGE_PIXELS = 25_000_000
Detector = Callable[[bytes], DetectionResult]


def bearer_token(authorization: str | None) -> str:
    scheme, _, token = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required")
    return token.strip()


async def read_limited_body(request: Request, limit: int) -> bytes:
    """Read a request body without buffering more than `limit` bytes."""
    declared = request.headers.get("content-length", "")
    if declared.isdigit() and int(declared) > limit:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Image is too large")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "Image is too large")
    return bytes(body)


def normalize_image(image_bytes: bytes) -> bytes:
    """Reject oversized dimensions before decoding, then create a small JPEG."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as image:
            if image.width * image.height > MAX_IMAGE_PIXELS:
                raise ValueError("Image dimensions are too large")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as error:
        raise ValueError("Unreadable image") from error
    return prepare_image(image_bytes)


def gemini_detector(settings: BackendSettings) -> Detector:
    provider = GeminiProvider(settings.gemini_api_key, settings.gemini_model)
    return lambda jpeg: parse_detection(provider.generate(jpeg))


def create_app(
    settings: BackendSettings | None = None,
    verifier: TokenVerifier | None = None,
    detector: Detector | None = None,
    limiter: RateLimiter | None = None,
) -> FastAPI:
    config = settings or load_backend_settings()
    token_verifier = verifier or FirebaseTokenVerifier(config.firebase_project_id)
    detect_dish = detector or gemini_detector(config)
    rate_limiter = limiter or RateLimiter(config.user_hourly_limit, config.global_daily_limit)
    app = FastAPI(title="SehtSnap API", docs_url=None, redoc_url=None, openapi_url=None)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/v1/detect", response_model=DetectionResult)
    async def detect(
        request: Request, authorization: str | None = Header(default=None)
    ) -> DetectionResult:
        token = bearer_token(authorization)
        try:
            uid = await run_in_threadpool(token_verifier.verify, token)
        except InvalidTokenError as error:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in required") from error
        except Exception as error:
            logger.warning("Token verification unavailable: %s", type(error).__name__)
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Service unavailable"
            ) from error

        content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if not content_type.startswith("image/"):
            raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, "Send an image")
        body = await read_limited_body(request, config.max_upload_bytes)
        try:
            jpeg = await run_in_threadpool(normalize_image, body)
        except ValueError as error:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_CONTENT, "Unreadable image"
            ) from error

        if not rate_limiter.allow(uid):
            raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, "Usage limit reached")
        try:
            return await run_in_threadpool(detect_dish, jpeg)
        except AIResponseError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, "Invalid AI response") from error
        except Exception as error:
            logger.warning("Gemini request failed: %s", type(error).__name__)
            raise HTTPException(
                status.HTTP_503_SERVICE_UNAVAILABLE, "Service unavailable"
            ) from error

    return app
