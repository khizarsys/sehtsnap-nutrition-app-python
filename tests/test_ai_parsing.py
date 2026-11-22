import io

import pytest
from PIL import Image

from sehtsnap.services.ai_vision_service import (
    BAD_RESPONSE_MESSAGE,
    INVALID_IMAGE_MESSAGE,
    MAX_IMAGE_SIDE,
    MISSING_KEY_MESSAGE,
    SERVICE_ERROR_MESSAGE,
    AIResponseError,
    AIVisionService,
    parse_detection,
    prepare_image,
)


class FakeProvider:
    def __init__(self, response: str = "", error: Exception | None = None) -> None:
        self.response = response
        self.error = error
        self.received: bytes | None = None

    def generate(self, jpeg_bytes: bytes) -> str:
        self.received = jpeg_bytes
        if self.error:
            raise self.error
        return self.response


def image_bytes(size: tuple[int, int] = (100, 80), image_format: str = "PNG") -> bytes:
    output = io.BytesIO()
    Image.new("RGBA" if image_format == "PNG" else "RGB", size, "orange").save(output, image_format)
    return output.getvalue()


def test_parse_valid_json():
    result = parse_detection(
        '{"dish": " Chicken   Biryani ", "confidence": 0.91, "serving_estimate": 1.5}'
    )
    assert result.dish == "Chicken Biryani"
    assert result.confidence == 0.91
    assert result.serving_estimate == 1.5


def test_parse_json_inside_code_fence():
    raw = '```json\n{"dish": "Nihari", "confidence": 0.8, "serving_estimate": 1}\n```'
    assert parse_detection(raw).dish == "Nihari"


@pytest.mark.parametrize(
    "raw",
    [
        "",
        "not json",
        "[]",
        '{"dish": "Daal"}',
        '{"dish": "", "confidence": 0.5, "serving_estimate": 1}',
        '{"dish": "Daal", "confidence": 1.5, "serving_estimate": 1}',
        '{"dish": "Daal", "confidence": 0.5, "serving_estimate": 0}',
    ],
)
def test_parse_rejects_invalid_responses(raw):
    with pytest.raises(AIResponseError):
        parse_detection(raw)


def test_prepare_image_resizes_and_converts_to_jpeg():
    prepared = prepare_image(image_bytes((3000, 1500)))
    with Image.open(io.BytesIO(prepared)) as image:
        assert image.format == "JPEG"
        assert max(image.size) == MAX_IMAGE_SIDE


def test_detect_success():
    provider = FakeProvider('{"dish": "Haleem", "confidence": 0.9, "serving_estimate": 1}')
    outcome = AIVisionService(provider).detect(image_bytes())
    assert outcome.result is not None
    assert outcome.result.dish == "Haleem"
    assert not outcome.needs_review
    assert provider.received is not None


def test_low_confidence_needs_review():
    provider = FakeProvider('{"dish": "Daal", "confidence": 0.59, "serving_estimate": 1}')
    assert AIVisionService(provider).detect(image_bytes()).needs_review


def test_non_food_needs_review():
    provider = FakeProvider('{"dish": "unknown", "confidence": 0, "serving_estimate": 1}')
    assert AIVisionService(provider).detect(image_bytes()).needs_review


def test_missing_key_is_friendly():
    outcome = AIVisionService(None).detect(image_bytes())
    assert outcome.error == MISSING_KEY_MESSAGE
    assert outcome.needs_review


def test_invalid_image_is_friendly():
    provider = FakeProvider("{}")
    outcome = AIVisionService(provider).detect(b"not an image")
    assert outcome.error == INVALID_IMAGE_MESSAGE
    assert provider.received is None


def test_invalid_json_is_friendly():
    outcome = AIVisionService(FakeProvider("oops")).detect(image_bytes())
    assert outcome.error == BAD_RESPONSE_MESSAGE


@pytest.mark.parametrize("error", [TimeoutError("slow"), RuntimeError("secret-value")])
def test_provider_errors_are_friendly(error, caplog):
    outcome = AIVisionService(FakeProvider(error=error)).detect(image_bytes())
    assert outcome.error == SERVICE_ERROR_MESSAGE
    assert "secret-value" not in caplog.text
