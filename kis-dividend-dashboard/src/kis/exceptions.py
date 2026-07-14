"""민감정보를 포함하지 않는 KIS 구조화 예외."""

from dataclasses import dataclass
from typing import override


class KisError(Exception):
    """한국투자증권 조회 경계의 기본 오류."""


@dataclass(frozen=True, slots=True)
class KisNetworkError(KisError):
    """timeout 또는 연결 실패."""

    reason: str

    @override
    def __str__(self) -> str:
        """안전한 네트워크 오류 문구를 반환합니다."""
        return f"한국투자증권 API 네트워크 오류: {self.reason}"


@dataclass(frozen=True, slots=True)
class KisAuthenticationError(KisError):
    """HTTP 또는 KIS 인증·토큰 오류."""

    status_code: int
    code: str = ""

    @override
    def __str__(self) -> str:
        """비밀정보 없는 인증 오류 문구를 반환합니다."""
        return f"한국투자증권 인증에 실패했습니다. HTTP {self.status_code} {self.code}".strip()


@dataclass(frozen=True, slots=True)
class KisApiRateLimitError(KisError):
    """HTTP 또는 KIS 호출 제한 오류."""

    code: str

    @override
    def __str__(self) -> str:
        """호출 제한 코드만 포함한 문구를 반환합니다."""
        return f"한국투자증권 API 호출 제한에 도달했습니다: {self.code}"


@dataclass(frozen=True, slots=True)
class KisApiResponseError(KisError):
    """성공 코드가 아닌 일반 KIS 응답."""

    code: str
    message: str

    @override
    def __str__(self) -> str:
        """KIS 오류 코드와 공개 메시지를 반환합니다."""
        return f"한국투자증권 API 오류 {self.code}: {self.message}"


@dataclass(frozen=True, slots=True)
class KisResponseValidationError(KisError):
    """필수 필드 또는 숫자 형식이 잘못된 외부 응답."""

    endpoint: str

    @override
    def __str__(self) -> str:
        """응답 원문 없이 endpoint만 반환합니다."""
        return f"한국투자증권 응답 형식이 공식 계약과 다릅니다: {self.endpoint}"


@dataclass(frozen=True, slots=True)
class KisPaginationError(KisError):
    """연속조회 상한 초과."""

    pages_requested: int

    @override
    def __str__(self) -> str:
        """조회된 페이지 수만 반환합니다."""
        return f"한국투자증권 연속조회가 {self.pages_requested}페이지 제한을 초과했습니다."


@dataclass(frozen=True, slots=True)
class KisReadOnlyViolationError(KisError):
    """허용 목록 밖 endpoint 호출 시도."""

    path: str

    @override
    def __str__(self) -> str:
        """비밀정보 없이 차단된 경로만 반환합니다."""
        return f"조회 전용 클라이언트에서 허용되지 않은 경로입니다: {self.path}"
