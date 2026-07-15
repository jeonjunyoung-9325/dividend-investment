from datetime import date

from src.demo_data import get_dividend_view


def test_demo_dividend_view_matches_production_page_contract() -> None:
    view = get_dividend_view()

    assert all(isinstance(value, date) for value in view.actual["지급일"])
    assert {"원화 세전", "원화 세금", "원화 실수령"} <= set(view.actual.columns)
    assert {"예상 세전 원화", "예상 세후 원화", "종목코드"} <= set(view.forecast.columns)
