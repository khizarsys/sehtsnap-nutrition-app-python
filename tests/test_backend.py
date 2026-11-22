import io

import httpx
import pytest
from fastapi.testclient import TestClient
from PIL import Image

from backend.app.auth import InvalidTokenError
from backend.app.config import BackendSettings
from backend.app.main import create_app
from backend.app.rate_limit import RateLimiter
from sehtsnap.models import DetectionResult
from sehtsnap.services.ai_vision_service import (
    AIResponseError,
    AIServiceError,
    AIVisionService,
    BackendProvider,
)

SETTINGS = BackendSettings(
    gemini_api_key="server-key", firebase_project_id="demo", max_upload_bytes=200_000
)
HEADERS = {"Authorization": "Bearer good", "Content-Type": "image/png"}


class FakeVerifier:
    def verify(self, token: str) -> str:
        if token != "good":
            raise InvalidTokenError
        return "user-1"


def png(size: tuple[int, int] = (32, 32)) -> bytes:
    output = io.BytesIO()
    Image.new("RGB", size, "orange").save(output, "PNG")
    return output.getvalue()


def client(detector=None, limiter=None) -> TestClient:
    result = DetectionResult(dish="Nihari", confidence=0.9, serving_estimate=1)
    app = create_app(
        SETTINGS,
        FakeVerifier(),
        detector or (lambda _: result),
        limiter or RateLimiter(10, 10),
    )
    return TestClient(app, raise_server_exceptions=False)


def test_health():
    assert client().get("/health").json() == {"status": "ok"}


def test_detect_success():
    response = client().post("/v1/detect", content=png(), headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["dish"] == "Nihari"


@pytest.mark.parametrize(
    "headers", [{}, {"Authorization": "Bearer bad"}, {"Authorization": "Basic x"}]
)
def test_invalid_auth_is_rejected_before_ai(headers):
    calls = []
    api = client(detector=lambda jpeg: calls.append(jpeg))
    response = api.post(
        "/v1/detect", content=png(), headers={"Content-Type": "image/png", **headers}
    )
    assert response.status_code == 401
    assert calls == []


def test_non_image_content_type_is_rejected():
    response = client().post(
        "/v1/detect", content=b"x", headers={**HEADERS, "Content-Type": "text/plain"}
    )
    assert response.status_code == 415


def test_unreadable_image_is_rejected():
    assert client().post("/v1/detect", content=b"nope", headers=HEADERS).status_code == 422


def test_large_upload_is_rejected():
    response = client().post("/v1/detect", content=b"x" * 200_001, headers=HEADERS)
    assert response.status_code == 413


def test_huge_dimensions_are_rejected():
    output = io.BytesIO()
    Image.new("1", (6000, 5000)).save(output, "PNG")
    assert (
        client().post("/v1/detect", content=output.getvalue(), headers=HEADERS).status_code == 422
    )


def test_rate_limit_returns_429():
    api = client(limiter=RateLimiter(1, 10))
    assert api.post("/v1/detect", content=png(), headers=HEADERS).status_code == 200
    assert api.post("/v1/detect", content=png(), headers=HEADERS).status_code == 429


def test_invalid_images_do_not_consume_quota():
    api = client(limiter=RateLimiter(1, 10))
    assert api.post("/v1/detect", content=b"nope", headers=HEADERS).status_code == 422
    assert api.post("/v1/detect", content=png(), headers=HEADERS).status_code == 200


def test_limiter_windows_expire():
    now = [0.0]
    limiter = RateLimiter(1, 2, clock=lambda: now[0])
    assert limiter.allow("a")
    assert not limiter.allow("a")
    assert limiter.allow("b")
    assert not limiter.allow("c")
    now[0] = 3601
    assert limiter.allow("a") is False
    now[0] = 86401
    assert limiter.allow("c")


def test_ai_errors_do_not_leak_details():
    def fail(_):
        raise RuntimeError("server-key leaked")

    response = client(detector=fail).post("/v1/detect", content=png(), headers=HEADERS)
    assert response.status_code == 503
    assert "server-key" not in response.text


def test_bad_ai_response_returns_502():
    def fail(_):
        raise AIResponseError("bad")

    assert (
        client(detector=fail).post("/v1/detect", content=png(), headers=HEADERS).status_code == 502
    )


def backend_provider(handler, token="token") -> BackendProvider:
    return BackendProvider(
        "https://api.example.com/",
        lambda: token,
        httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_client_sends_token_and_image():
    seen = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(
            url=str(request.url), auth=request.headers["authorization"], body=request.content
        )
        return httpx.Response(
            200, json={"dish": "Haleem", "confidence": 0.8, "serving_estimate": 1}
        )

    outcome = AIVisionService(backend_provider(handler)).detect(png())
    assert outcome.result.dish == "Haleem"
    assert seen["url"] == "https://api.example.com/v1/detect"
    assert seen["auth"] == "Bearer token"
    assert seen["body"].startswith(b"\xff\xd8")


@pytest.mark.parametrize(
    ("status_code", "text"), [(401, "sign in"), (429, "limit"), (503, "unavailable")]
)
def test_client_maps_backend_errors(status_code, text):
    outcome = AIVisionService(
        backend_provider(lambda _: httpx.Response(status_code, json={}))
    ).detect(png())
    assert text in outcome.error.lower()


def test_client_requires_token():
    provider = backend_provider(lambda _: httpx.Response(200), token="")
    with pytest.raises(AIServiceError):
        provider.generate(b"jpeg")


@pytest.mark.parametrize("url", ["http://api.example.com", "ftp://api.example.com", "not-a-url"])
def test_client_rejects_insecure_urls(url):
    with pytest.raises(ValueError):
        BackendProvider(url, lambda: "token")


def test_client_allows_localhost_for_development():
    BackendProvider("http://127.0.0.1:8080", lambda: "token")
