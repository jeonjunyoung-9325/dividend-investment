from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pandas as pd

from src.ui.formatting import money
from src.ui.viewmodels import (
    CalendarView,
    DashboardView,
    DividendView,
    EditableSettingView,
    HistoryView,
    MetricView,
    PortfolioView,
    SourceView,
    SyncView,
)

NOW = datetime(2026, 7, 14, 12, 0, tzinfo=UTC)
SOURCE = SourceView("DEMO_MODE 샘플 데이터", NOW, NOW, is_realtime=False)
SYNC = SyncView("success", "가상 데이터 동기화가 완료되었습니다.", NOW, "not_used", 5, 0)


def get_dashboard_view() -> DashboardView:
    positions = _positions()
    monthly = _monthly_dividends()
    history = _asset_history().rename(
        columns={
            "date": "날짜",
            "total_value_krw": "총 평가자산",
            "domestic_value_krw": "국내",
            "overseas_value_krw": "해외",
        }
    )
    metrics = (
        MetricView(
            "총 평가자산", money(Decimal(152340000)), "+1,240,000원", "neutral", "2026-07-14 기준"
        ),
        MetricView("국내주식 평가금액", money(Decimal(68340000))),
        MetricView("해외주식 평가금액", money(Decimal(84000000))),
        MetricView("총 평가손익", money(Decimal(12340000)), "+8.81%"),
        MetricView("올해 실수령 배당금", money(Decimal(1534200)), kind="actual"),
        MetricView("최근 12개월 실수령", money(Decimal(2418000)), kind="actual"),
        MetricView("확정 예정 배당금", money(Decimal(486000)), kind="confirmed"),
        MetricView("향후 12개월 예상 세전", money(Decimal(5290000)), kind="estimated"),
        MetricView(
            "향후 12개월 예상 세후",
            money(Decimal(4482000)),
            kind="estimated",
            help_text="단순 세율 가정",
        ),
    )
    allocation = pd.DataFrame({"시장": ["국내", "해외"], "평가금액": [68340000, 84000000]})
    weights = positions[["종목명", "원화 평가금액"]].copy()
    contributions = pd.DataFrame(
        {
            "종목명": ["SCHD", "JEPI", "O", "삼성전자", "V"],
            "예상 배당금": [1420000, 1280000, 1090000, 840000, 660000],
        }
    )
    cumulative = monthly[["월", "실제"]].copy()
    cumulative["누적 실수령"] = cumulative["실제"].cumsum()
    return DashboardView(
        metrics, allocation, weights, contributions, monthly, history, cumulative, SOURCE, SYNC
    )


def get_portfolio_view() -> PortfolioView:
    return PortfolioView(_positions(), SOURCE)


def get_dividend_view() -> DividendView:
    actual = pd.DataFrame(
        [
            ["SCHD", "2026-06-30", "실제", 420000, 63000, 357000, "USD", "사용자 업로드"],
            ["삼성전자", "2026-05-20", "실제", 216000, 33264, 182736, "KRW", "사용자 업로드"],
        ],
        columns=["종목", "지급일", "구분", "세전", "세금", "실수령", "통화", "출처"],
    )
    confirmed = pd.DataFrame(
        [
            [
                "JEPI",
                "2026-08-01",
                "2026-08-05",
                "2026-08-12",
                "확정",
                "확인 필요",
                "공식 권리 일정",
            ],
            [
                "KT&G",
                "2026-06-29",
                "2026-06-30",
                "2026-08-25",
                "확정",
                "자격 확인",
                "공식 배당 일정",
            ],
        ],
        columns=["종목", "배당락일", "기준일", "지급일", "구분", "수령 자격", "출처"],
    )
    forecast = pd.DataFrame(
        [
            ["SCHD", "최근 4회 합계", "분기", 4, 1420000, 1207000, "높음"],
            ["JEPI", "6개월 중앙값 연환산", "월", 6, 1280000, 1088000, "높음"],
            ["O", "6개월 중앙값 연환산", "월", 6, 1090000, 926500, "높음"],
            ["V", "예측 불가", "판단 불가", 1, None, None, "데이터 부족"],
        ],
        columns=["종목", "예측 방식", "지급 주기", "표본 수", "예상 세전", "예상 세후", "신뢰도"],
    )
    dates = pd.date_range("2025-08-01", periods=12, freq="MS")
    history = pd.DataFrame(
        {
            "종목": ["JEPI"] * 12,
            "지급일": dates.date,
            "주당 배당금": [Decimal("0.35") + Decimal(index) / Decimal(100) for index in range(12)],
            "출처": ["샘플"] * 12,
        }
    )
    return DividendView(actual, confirmed, forecast, history, SOURCE)


def get_calendar_view() -> CalendarView:
    events = pd.DataFrame(
        [
            [date(2026, 8, 1), "JEPI", "배당락일", "확정"],
            [date(2026, 8, 12), "JEPI", "지급일", "확정"],
            [date(2026, 9, 1), "O", "예상 지급일", "예상"],
        ],
        columns=["event_date", "symbol", "event_type", "status"],
    )
    return CalendarView(events, SOURCE)


def get_history_view() -> HistoryView:
    return HistoryView(_asset_history(), SOURCE)


def get_editable_settings() -> EditableSettingView:
    return EditableSettingView(
        "KRW", Decimal("0.154"), Decimal("0.15"), Decimal("0.20"), ("NASD", "NYSE", "AMEX"), 2
    )


def save_editable_settings(settings: EditableSettingView) -> None:
    del settings


def synchronize_demo() -> SyncView:
    return SYNC


def _positions() -> pd.DataFrame:
    return pd.DataFrame(
        [
            ["국내", "KRX", "005930", "삼성전자", Decimal(120), "KRW", 9360000, 360000, 4.0],
            ["국내", "KRX", "033780", "KT&G", Decimal(60), "KRW", 5940000, 240000, 4.2],
            [
                "해외",
                "NYSE",
                "SCHD",
                "Schwab US Dividend ETF",
                Decimal(80),
                "USD",
                38400000,
                3200000,
                9.1,
            ],
            [
                "해외",
                "NYSE",
                "JEPI",
                "JPMorgan Equity Premium Income",
                Decimal(70),
                "USD",
                30100000,
                2100000,
                7.5,
            ],
            ["해외", "NYSE", "O", "Realty Income", Decimal(45), "USD", 15500000, -320000, -2.0],
        ],
        columns=[
            "시장",
            "거래소",
            "종목코드",
            "종목명",
            "수량",
            "통화",
            "원화 평가금액",
            "원화 평가손익",
            "수익률",
        ],
    )


def _monthly_dividends() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "월": [f"{month}월" for month in range(1, 13)],
            "실제": [120000, 80000, 190000, 130000, 182736, 357000, 160000, 0, 0, 0, 0, 0],
            "확정": [0, 0, 0, 0, 0, 0, 0, 243000, 243000, 0, 0, 0],
            "예상": [
                380000,
                410000,
                450000,
                390000,
                470000,
                510000,
                420000,
                460000,
                480000,
                430000,
                450000,
                440000,
            ],
        }
    )


def _asset_history() -> pd.DataFrame:
    days = [NOW.date() - timedelta(days=offset) for offset in range(29, -1, -1)]
    return pd.DataFrame(
        {
            "date": days,
            "total_value_krw": [
                148000000 + index * 145000 + (index % 4) * 70000 for index in range(30)
            ],
            "domestic_value_krw": [67000000 + index * 46000 for index in range(30)],
            "overseas_value_krw": [81000000 + index * 99000 for index in range(30)],
        }
    )
