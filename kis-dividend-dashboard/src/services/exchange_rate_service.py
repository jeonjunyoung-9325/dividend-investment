from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from src.repositories.exchange_rates import latest_rate, upsert_rate
from src.schemas import ExchangeRateQuote

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def rate_for_currency(
    session: Session,
    currency: str,
    *,
    default_usd_krw: Decimal,
    now: datetime | None = None,
) -> ExchangeRateQuote | None:
    instant = now or datetime.now(UTC)
    code = currency.upper()
    if code == "KRW":
        return ExchangeRateQuote(
            base_currency="KRW",
            quote_currency="KRW",
            rate=Decimal(1),
            rate_date=instant.date(),
            fetched_at=instant,
            source="identity",
            is_realtime=False,
        )
    stored = latest_rate(session, code)
    if stored is not None:
        return ExchangeRateQuote(
            base_currency=stored.base_currency,
            quote_currency=stored.quote_currency,
            rate=stored.rate,
            rate_date=stored.rate_date,
            fetched_at=stored.fetched_at,
            source=stored.source,
            is_realtime=False,
            is_last_known=True,
        )
    if code != "USD" or default_usd_krw <= 0:
        return None
    quote = ExchangeRateQuote(
        base_currency="USD",
        quote_currency="KRW",
        rate=default_usd_krw,
        rate_date=instant.date(),
        fetched_at=instant,
        source="user_default",
        is_realtime=False,
        is_last_known=False,
    )
    upsert_rate(session, quote)
    return quote
