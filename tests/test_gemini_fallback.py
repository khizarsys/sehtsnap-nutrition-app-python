from types import SimpleNamespace

import httpx
import pytest

from sehtsnap.services.ai_vision_service import GeminiProvider


class StatusError(Exception):
    def __init__(self, code: int) -> None:
        super().__init__(f"status {code}")
        self.code = code


class FakeClient:
    def __init__(self, outcomes: dict[str, object]) -> None:
        self.outcomes = outcomes
        self.calls: list[str] = []
        self.models = SimpleNamespace(generate_content=self.generate_content)

    def generate_content(self, model: str, contents: list, config: object) -> SimpleNamespace:
        self.calls.append(model)
        outcome = self.outcomes[model]
        if isinstance(outcome, Exception):
            raise outcome
        return SimpleNamespace(text=outcome)


class Httpx2TransportError(Exception):
    pass


Httpx2TransportError.__name__ = "TransportError"
Httpx2TransportError.__module__ = "httpx2._exceptions"


class Httpx2ReadTimeout(Httpx2TransportError):
    pass


def provider(client: FakeClient) -> GeminiProvider:
    return GeminiProvider("key", "first", ("second", "third"), client=client)


@pytest.mark.parametrize(
    "failure",
    [
        TimeoutError("slow"),
        ConnectionError("offline"),
        Httpx2ReadTimeout("slow"),
        StatusError(404),
    ],
)
def test_transport_failures_use_next_model(failure):
    client = FakeClient({"first": failure, "second": "ok", "third": "unused"})
    assert provider(client).generate(b"jpeg") == "ok"
    assert client.calls == ["first", "second"]


@pytest.mark.parametrize("failure", [StatusError(503), StatusError(429), httpx.ReadTimeout("slow")])
def test_temporary_failure_uses_next_model(failure):
    client = FakeClient({"first": failure, "second": "ok", "third": "unused"})
    assert provider(client).generate(b"jpeg") == "ok"
    assert client.calls == ["first", "second"]


def test_permanent_failure_does_not_try_other_models():
    client = FakeClient({"first": StatusError(400), "second": "ok", "third": "ok"})
    with pytest.raises(StatusError):
        provider(client).generate(b"jpeg")
    assert client.calls == ["first"]


def test_all_models_unavailable_raises_last_error():
    client = FakeClient(
        {"first": StatusError(503), "second": StatusError(500), "third": StatusError(429)}
    )
    with pytest.raises(StatusError) as error:
        provider(client).generate(b"jpeg")
    assert error.value.code == 429
    assert client.calls == ["first", "second", "third"]


def test_duplicate_models_are_called_once():
    client = FakeClient({"first": StatusError(503), "second": "ok"})
    gemini = GeminiProvider("key", "first", ("first", "second"), client=client)
    assert gemini.generate(b"jpeg") == "ok"
    assert client.calls == ["first", "second"]
