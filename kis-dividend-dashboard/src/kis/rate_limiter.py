"""공식 수치로 오인하지 않는 최소 호출 간격 보조 제한기."""

import threading
import time
from typing import Protocol, final


class RateLimiter(Protocol):
    """클라이언트 호출 직전 대기 계약."""

    def wait(self) -> None:
        """필요한 호출 간격만큼 대기합니다."""
        ...


@final
class IntervalRateLimiter:
    """호출 간 최소 간격을 직렬화하는 프로세스 내 보조 제한기."""

    def __init__(self, minimum_interval_seconds: float = 0.1) -> None:
        """공식 저장소 샘플의 0.1초 기본 간격으로 초기화합니다."""
        self.minimum_interval_seconds: float = minimum_interval_seconds
        self._lock: threading.Lock = threading.Lock()
        self._last_called_at: float = 0.0

    def wait(self) -> None:
        """같은 프로세스의 직전 호출 이후 남은 간격만 대기합니다."""
        with self._lock:
            now = time.monotonic()
            remaining = self.minimum_interval_seconds - (now - self._last_called_at)
            if remaining > 0:
                time.sleep(remaining)
            self._last_called_at = time.monotonic()
