import pytest
from src.kis.exceptions import KisPaginationError
from src.kis.pagination import Cursor, Page, collect_pages


def test_collect_pages_returns_all_items_when_continuation_exists() -> None:
    # Given
    seen: list[Cursor] = []

    def fetch(cursor: Cursor) -> Page[int]:
        seen.append(cursor)
        if cursor.fk == "":
            return Page(items=(1,), next_cursor=Cursor("fk2", "nk2"), has_more=True)
        return Page(items=(2,), next_cursor=Cursor("", ""), has_more=False)

    # When
    result = collect_pages(fetch)

    # Then
    assert result == (1, 2)
    assert seen == [Cursor("", ""), Cursor("fk2", "nk2")]


def test_collect_pages_raises_when_limit_is_reached() -> None:
    # Given
    def fetch(_cursor: Cursor) -> Page[int]:
        return Page(items=(1,), next_cursor=Cursor("same", "same"), has_more=True)

    # When / Then
    with pytest.raises(KisPaginationError) as raised:
        _ = collect_pages(fetch, max_pages=2)
    assert raised.value.pages_requested == 2
