from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.models import ExchangeRate

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.schemas import ExchangeRateQuote


def latest_rate(
    session: Session, base_currency: str, quote_currency: str = "KRW"
) -> ExchangeRate | None:
    return session.scalar(
        select(ExchangeRate)
        .where(
            ExchangeRate.base_currency == base_currency.upper(),
            ExchangeRate.quote_currency == quote_currency.upper(),
        )
        .order_by(ExchangeRate.rate_date.desc(), ExchangeRate.fetched_at.desc())
        .limit(1)
    )


def upsert_rate(session: Session, quote: ExchangeRateQuote) -> tuple[int, int]:
    statement = select(ExchangeRate).where(
        ExchangeRate.rate_date == quote.rate_date,
        ExchangeRate.base_currency == quote.base_currency.upper(),
        ExchangeRate.quote_currency == quote.quote_currency.upper(),
        ExchangeRate.source == quote.source,
    )
    row = session.scalar(statement)
    if row is None:
        session.add(
            ExchangeRate(
                rate_date=quote.rate_date,
                base_currency=quote.base_currency.upper(),
                quote_currency=quote.quote_currency.upper(),
                rate=quote.rate,
                source=quote.source,
                fetched_at=quote.fetched_at,
            )
        )
        session.flush()
        return 1, 0
    row.rate = quote.rate
    row.fetched_at = quote.fetched_at
    session.flush()
    return 0, 1
