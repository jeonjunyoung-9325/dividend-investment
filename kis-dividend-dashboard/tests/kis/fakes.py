from collections import deque
from dataclasses import dataclass

from src.kis.transport import HttpRequest, HttpResponse


class FakeTransport:
    def __init__(self, responses: deque[HttpResponse]) -> None:
        self.responses: deque[HttpResponse] = responses
        self.requests: list[HttpRequest] = []

    def send(self, request: HttpRequest) -> HttpResponse:
        self.requests.append(request)
        return self.responses.popleft()


@dataclass(frozen=True, slots=True)
class StaticTokenProvider:
    value: str = "opaque-test-value"

    def get_access_token(self) -> str:
        return self.value
