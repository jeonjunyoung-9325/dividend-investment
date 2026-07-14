"""KIS 연속조회 cursor를 제한된 횟수로 수집합니다."""

from collections.abc import Callable
from dataclasses import dataclass

from src.kis.exceptions import KisPaginationError


@dataclass(frozen=True, slots=True)
class Cursor:
    """KIS 응답의 FK·NK 연속조회 키."""

    fk: str
    nk: str


@dataclass(frozen=True, slots=True)
class Page[T]:
    """정규화된 한 페이지와 다음 cursor 상태."""

    items: tuple[T, ...]
    next_cursor: Cursor
    has_more: bool


def collect_pages[T](fetch: Callable[[Cursor], Page[T]], *, max_pages: int = 10) -> tuple[T, ...]:
    """첫 빈 cursor부터 종료 페이지까지 항목을 순서대로 합칩니다."""
    cursor = Cursor("", "")
    collected: list[T] = []
    for _page_number in range(1, max_pages + 1):
        page = fetch(cursor)
        collected.extend(page.items)
        if not page.has_more:
            return tuple(collected)
        cursor = page.next_cursor
    raise KisPaginationError(pages_requested=max_pages)
