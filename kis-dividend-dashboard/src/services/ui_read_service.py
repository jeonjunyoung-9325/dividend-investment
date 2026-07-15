from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from functools import lru_cache
from typing import TYPE_CHECKING, Literal, cast

import pandas as pd

from src.calculations.dividend_forecast import ForecastMethod
from src.config import get_settings
from src.database import create_database_engine, create_session_factory
from src.repositories.dividends import list_events, list_payments
from src.repositories.positions import latest_snapshot_at, list_latest_positions
from src.repositories.settings import get_setting, set_setting
from src.repositories.snapshots import asset_history
from src.repositories.sync_runs import latest_run
from src.services.dividend_forecast_service import ForecastEvidence, ForecastTaxRates, forecast_rows
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
    SymbolForecastOverride,
    SyncView,
)

if TYPE_CHECKING:
    from sqlalchemy.orm import Session, sessionmaker

    from src.models import DividendPayment, PortfolioSnapshot

DEFAULT_EDITABLE = EditableSettingView(
    display_currency="KRW",
    domestic_tax_rate=Decimal("0.154"),
    us_tax_rate=Decimal("0.15"),
    overseas_tax_rate=Decimal("0.20"),
    enabled_exchanges=("NASD",),
    decimal_places=2,
)


@lru_cache(maxsize=1)
def session_factory() -> sessionmaker[Session]:
    settings = get_settings()
    settings.validate_runtime()
    engine = create_database_engine(settings.SUPABASE_DB_URL.get_secret_value())
    return create_session_factory(engine)


def get_portfolio_view() -> PortfolioView:
    with session_factory()() as session:
        positions = list_latest_positions(session)
        return PortfolioView(_position_frame(positions), _source(session))


def get_dividend_view() -> DividendView:
    with session_factory()() as session:
        positions = list_latest_positions(session)
        payments = list_payments(session)
        events = list_events(session)
        editable = _load_editable(session)
        forecasts = forecast_rows(
            positions,
            ForecastEvidence(payments, events),
            as_of=datetime.now(UTC).date(),
            tax_rates=ForecastTaxRates(
                editable.domestic_tax_rate,
                editable.us_tax_rate,
                editable.overseas_tax_rate,
            ),
            symbol_overrides={
                item.symbol: (
                    item.tax_rate,
                    ForecastMethod(item.forecast_method) if item.forecast_method else None,
                    item.manual_annual_per_share,
                )
                for item in editable.symbol_overrides
            },
        )
        actual = pd.DataFrame(
            [
                {
                    "종목": row.name,
                    "지급일": row.payment_date,
                    "구분": "실제",
                    "세전": row.gross_amount,
                    "세금": row.tax_amount,
                    "실수령": row.net_amount,
                    "통화": row.currency,
                    "원화 세전": _krw_amount(row, "gross"),
                    "원화 세금": _krw_amount(row, "tax"),
                    "원화 실수령": _krw_payment(row),
                    "출처": row.source,
                }
                for row in payments
            ],
            columns=[
                "종목",
                "지급일",
                "구분",
                "세전",
                "세금",
                "실수령",
                "통화",
                "원화 세전",
                "원화 세금",
                "원화 실수령",
                "출처",
            ],
        )
        confirmed = pd.DataFrame(
            [
                {
                    "종목": row.symbol,
                    "배당락일": row.ex_dividend_date,
                    "기준일": row.record_date,
                    "지급일": row.payment_date,
                    "주당 배당금": row.amount_per_share,
                    "구분": "발표됨",
                    "수령 자격": "확인 필요",
                    "통화": row.currency,
                    "출처": row.source,
                }
                for row in events
                if row.status in {"confirmed", "announced_unverified"}
            ]
        )
        history = pd.DataFrame(
            [
                {
                    "종목": row.name,
                    "지급일": row.payment_date,
                    "주당 배당금": row.amount_per_share,
                    "통화": row.currency,
                    "출처": row.source,
                }
                for row in payments
                if row.amount_per_share is not None
            ]
            + [
                {
                    "종목": row.symbol,
                    "지급일": row.payment_date or row.record_date or row.ex_dividend_date,
                    "주당 배당금": row.amount_per_share,
                    "통화": row.currency,
                    "출처": row.source,
                }
                for row in events
                if (row.payment_date or row.record_date or row.ex_dividend_date) is not None
            ]
        )
        forecast_frame = pd.DataFrame(forecasts)
        monthly = _monthly_frame(payments, forecast_frame)
        return DividendView(actual, confirmed, forecast_frame, history, monthly, _source(session))


def get_calendar_view() -> CalendarView:
    with session_factory()() as session:
        rows: list[dict[str, object]] = []
        for event in list_events(session):
            status = "확정" if event.status == "confirmed" else "발표·자격 미확인"
            for event_type, event_date in (
                ("배당락일", event.ex_dividend_date),
                ("기준일", event.record_date),
                ("지급일", event.payment_date),
            ):
                if event_date is not None:
                    rows.append(
                        {
                            "event_date": event_date,
                            "symbol": event.symbol,
                            "event_type": event_type,
                            "status": status,
                        }
                    )
        return CalendarView(
            pd.DataFrame(rows, columns=["event_date", "symbol", "event_type", "status"]),
            _source(session),
        )


def get_history_view() -> HistoryView:
    with session_factory()() as session:
        rows = asset_history(session)
        frame = pd.DataFrame(
            [
                {
                    "date": instant.date(),
                    "total_value_krw": total,
                    "domestic_value_krw": domestic,
                    "overseas_value_krw": overseas,
                }
                for instant, total, domestic, overseas in rows
            ],
            columns=["date", "total_value_krw", "domestic_value_krw", "overseas_value_krw"],
        )
        return HistoryView(frame, _source(session))


def get_dashboard_view() -> DashboardView:
    portfolio = get_portfolio_view()
    dividends = get_dividend_view()
    history = get_history_view()
    with session_factory()() as session:
        payments = list_payments(session)
        sync = _sync_view(session)
    positions = portfolio.positions
    domestic = _sum_column(positions.loc[positions["시장"] == "국내"], "원화 평가금액")
    overseas = _sum_column(positions.loc[positions["시장"] == "해외"], "원화 평가금액")
    profit = _sum_column(positions, "원화 평가손익")
    now = datetime.now(UTC).date()
    year_net = sum(
        (_krw_payment(row) for row in payments if row.payment_date.year == now.year), Decimal(0)
    )
    cutoff = now - timedelta(days=365)
    rolling_net = sum(
        (_krw_payment(row) for row in payments if row.payment_date >= cutoff), Decimal(0)
    )
    forecast_gross = _sum_column(dividends.forecast, "예상 세전 원화")
    forecast_net = _sum_column(dividends.forecast, "예상 세후 원화")
    metrics = (
        MetricView("총 평가자산", money(domestic + overseas)),
        MetricView("국내주식 평가금액", money(domestic)),
        MetricView("해외주식 평가금액", money(overseas)),
        MetricView("총 평가손익", money(profit)),
        MetricView("올해 실수령 배당금", money(year_net), kind="actual"),
        MetricView("최근 12개월 실수령", money(rolling_net), kind="actual"),
        MetricView("확정 예정 배당금", "수령 자격 확인 필요", kind="confirmed"),
        MetricView("향후 12개월 예상 세전", money(forecast_gross), kind="estimated"),
        MetricView("향후 12개월 예상 세후", money(forecast_net), kind="estimated"),
    )
    allocation = pd.DataFrame({"시장": ["국내", "해외"], "평가금액": [domestic, overseas]})
    weights = (
        positions[["종목명", "원화 평가금액"]].copy()
        if not positions.empty
        else pd.DataFrame(columns=["종목명", "원화 평가금액"])
    )
    contributions = dividends.forecast.rename(
        columns={"종목": "종목명", "예상 세전 원화": "예상 배당금"}
    )
    contributions = (
        contributions[["종목명", "예상 배당금"]]
        if not contributions.empty
        else pd.DataFrame(columns=["종목명", "예상 배당금"])
    )
    monthly = dividends.monthly
    cumulative = monthly[["월", "실제"]].copy()
    cumulative["누적 실수령"] = cumulative["실제"].cumsum()
    home_history = history.snapshots.rename(
        columns={
            "date": "날짜",
            "total_value_krw": "총 평가자산",
            "domestic_value_krw": "국내",
            "overseas_value_krw": "해외",
        }
    )
    return DashboardView(
        metrics,
        allocation,
        weights,
        contributions,
        monthly,
        home_history,
        cumulative,
        portfolio.source,
        sync,
    )


def get_editable_settings() -> EditableSettingView:
    with session_factory()() as session:
        return _load_editable(session)


def save_editable_settings(settings: EditableSettingView) -> None:
    with session_factory()() as session, session.begin():
        set_setting(session, "display_currency", {"value": settings.display_currency})
        set_setting(session, "domestic_tax_rate", {"value": str(settings.domestic_tax_rate)})
        set_setting(session, "us_tax_rate", {"value": str(settings.us_tax_rate)})
        set_setting(session, "overseas_tax_rate", {"value": str(settings.overseas_tax_rate)})
        set_setting(session, "enabled_exchanges", {"value": ",".join(settings.enabled_exchanges)})
        set_setting(session, "decimal_places", {"value": settings.decimal_places})
        set_setting(
            session,
            "symbol_overrides",
            {
                "value": json.dumps(
                    [
                        {
                            "symbol": row.symbol,
                            "tax_rate": str(row.tax_rate) if row.tax_rate is not None else None,
                            "forecast_method": row.forecast_method,
                            "manual_annual_per_share": (
                                str(row.manual_annual_per_share)
                                if row.manual_annual_per_share is not None
                                else None
                            ),
                        }
                        for row in settings.symbol_overrides
                    ],
                    ensure_ascii=False,
                )
            },
        )


def _load_editable(session: Session) -> EditableSettingView:
    def value(key: str, fallback: str | int | Decimal) -> str | int | bool | Decimal:
        stored = get_setting(session, key)
        return fallback if stored is None else stored.get("value", fallback)

    exchanges = str(value("enabled_exchanges", ",".join(DEFAULT_EDITABLE.enabled_exchanges)))
    raw_overrides = str(value("symbol_overrides", "[]"))
    parsed_overrides = json.loads(raw_overrides)
    return EditableSettingView(
        str(value("display_currency", DEFAULT_EDITABLE.display_currency)),
        Decimal(str(value("domestic_tax_rate", DEFAULT_EDITABLE.domestic_tax_rate))),
        Decimal(str(value("us_tax_rate", DEFAULT_EDITABLE.us_tax_rate))),
        Decimal(str(value("overseas_tax_rate", DEFAULT_EDITABLE.overseas_tax_rate))),
        tuple(item for item in exchanges.split(",") if item),
        int(value("decimal_places", DEFAULT_EDITABLE.decimal_places)),
        tuple(
            SymbolForecastOverride(
                symbol=str(row["symbol"]),
                tax_rate=Decimal(str(row["tax_rate"])) if row.get("tax_rate") else None,
                forecast_method=row.get("forecast_method"),
                manual_annual_per_share=(
                    Decimal(str(row["manual_annual_per_share"]))
                    if row.get("manual_annual_per_share")
                    else None
                ),
            )
            for row in parsed_overrides
            if isinstance(row, dict) and row.get("symbol")
        ),
    )


def _position_frame(positions: tuple[PortfolioSnapshot, ...]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "시장": "국내" if row.market == "domestic" else "해외",
                "거래소": row.exchange,
                "종목코드": row.symbol,
                "종목명": row.name,
                "수량": row.quantity,
                "평균단가": row.average_price,
                "현재가": row.current_price,
                "매입금액": row.purchase_amount,
                "평가금액": row.evaluation_amount,
                "원화 평가금액": row.evaluation_amount_krw,
                "원화 평가손익": row.profit_loss_krw,
                "수익률": row.profit_rate,
                "통화": row.currency,
                "조회 시각": row.snapshot_at,
                "출처": row.source,
            }
            for row in positions
        ],
        columns=[
            "시장",
            "거래소",
            "종목코드",
            "종목명",
            "수량",
            "평균단가",
            "현재가",
            "매입금액",
            "평가금액",
            "원화 평가금액",
            "원화 평가손익",
            "수익률",
            "통화",
            "조회 시각",
            "출처",
        ],
    )


def _source(session: Session) -> SourceView:
    instant = latest_snapshot_at(session) or datetime.now(UTC)
    return SourceView(
        source="Supabase PostgreSQL / KIS Open API",
        as_of=instant,
        fetched_at=instant,
        is_realtime=False,
        using_last_saved=latest_snapshot_at(session) is None,
    )


def _sync_view(session: Session) -> SyncView:
    run = latest_run(session)
    good = latest_run(session, successful_only=True)
    if run is None:
        return SyncView("idle", "아직 동기화하지 않았습니다.", None, "not_used")
    state = cast(
        "Literal['success', 'partial', 'failed', 'running']",
        run.status if run.status in {"success", "partial", "failed"} else "running",
    )
    return SyncView(
        state,
        run.message or "동기화 상태를 확인했습니다.",
        good.finished_at if good else None,
        "not_used",
        run.records_inserted,
        run.records_updated,
    )


def _krw_payment(payment: DividendPayment) -> Decimal:
    return _krw_amount(payment, "net")


def _krw_amount(payment: DividendPayment, kind: Literal["gross", "tax", "net"]) -> Decimal:
    converted = getattr(payment, f"{kind}_amount_krw")
    if converted is not None:
        return converted
    original = getattr(payment, f"{kind}_amount")
    return original if payment.currency == "KRW" else Decimal(0)


def _sum_column(frame: pd.DataFrame, column: str) -> Decimal:
    if frame.empty or column not in frame:
        return Decimal(0)
    return sum(
        (value for value in frame[column] if value is not None and not pd.isna(value)), Decimal(0)
    )


def _monthly_frame(payments: tuple[DividendPayment, ...], forecasts: pd.DataFrame) -> pd.DataFrame:
    current = datetime.now(UTC).year
    actual = {month: Decimal(0) for month in range(1, 13)}
    estimated = {month: Decimal(0) for month in range(1, 13)}
    for payment in payments:
        if payment.payment_date.year == current:
            actual[payment.payment_date.month] += _krw_payment(payment)
    if not forecasts.empty:
        for _, row in forecasts.iterrows():
            count = row.get("연간 예상 지급 횟수")
            gross = row.get("예상 세전 원화")
            latest = row.get("마지막 데이터")
            if count is None or gross is None or latest is None or pd.isna(count):
                continue
            payments_per_year = int(count)
            if payments_per_year <= 0:
                continue
            interval = max(1, 12 // payments_per_year)
            installment = gross / Decimal(payments_per_year)
            for offset in range(1, payments_per_year + 1):
                month = ((latest.month - 1 + interval * offset) % 12) + 1
                estimated[month] += installment
    return pd.DataFrame(
        {
            "월": [f"{month}월" for month in actual],
            "실제": list(actual.values()),
            "확정": [Decimal(0)] * 12,
            "예상": list(estimated.values()),
        }
    )
