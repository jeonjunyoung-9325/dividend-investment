from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import select

from src.models import DividendEvent, DividendPayment

if TYPE_CHECKING:
    from collections.abc import Iterable
    from datetime import date

    from sqlalchemy.orm import Session

    from src.schemas import DividendPaymentInput


def list_payments(
    session: Session, *, start_date: date | None = None
) -> tuple[DividendPayment, ...]:
    statement = select(DividendPayment)
    if start_date is not None:
        statement = statement.where(DividendPayment.payment_date >= start_date)
    return tuple(session.scalars(statement.order_by(DividendPayment.payment_date)))


def list_events(session: Session) -> tuple[DividendEvent, ...]:
    return tuple(
        session.scalars(
            select(DividendEvent).order_by(
                DividendEvent.payment_date, DividendEvent.record_date, DividendEvent.symbol
            )
        )
    )


def insert_payments(session: Session, rows: Iterable[DividendPaymentInput]) -> tuple[int, int]:
    hashes = {row.import_hash for row in rows}
    existing: set[str] = (
        {
            value
            for value in session.scalars(
                select(DividendPayment.import_hash).where(DividendPayment.import_hash.in_(hashes))
            )
            if value is not None
        }
        if hashes
        else set()
    )
    inserted = 0
    excluded = 0
    for row in rows:
        if row.import_hash in existing:
            excluded += 1
            continue
        rate = row.krw_exchange_rate
        session.add(
            DividendPayment(
                market=row.market.value,
                exchange=row.exchange,
                symbol=row.symbol,
                name=row.name,
                payment_date=row.payment_date,
                quantity_at_record_date=row.quantity_at_record_date,
                gross_amount=row.gross_amount,
                tax_amount=row.tax_amount,
                net_amount=row.net_amount,
                amount_per_share=row.amount_per_share,
                currency=row.currency,
                krw_exchange_rate=rate,
                gross_amount_krw=row.gross_amount * rate if rate else None,
                tax_amount_krw=row.tax_amount * rate if rate else None,
                net_amount_krw=row.net_amount * rate if rate else None,
                source=row.source,
                import_hash=row.import_hash,
            )
        )
        existing.add(row.import_hash)
        inserted += 1
    session.flush()
    return inserted, excluded


def existing_import_hashes(session: Session, hashes: set[str]) -> set[str]:
    if not hashes:
        return set()
    return {
        value
        for value in session.scalars(
            select(DividendPayment.import_hash).where(DividendPayment.import_hash.in_(hashes))
        )
        if value is not None
    }


def upsert_events(session: Session, events: Iterable[DividendEvent]) -> tuple[int, int]:
    values = tuple(events)
    keys = {event.event_key for event in values}
    existing = (
        {
            event.event_key: event
            for event in session.scalars(
                select(DividendEvent).where(DividendEvent.event_key.in_(keys))
            )
        }
        if keys
        else {}
    )
    inserted = 0
    updated = 0
    for event in values:
        row = existing.get(event.event_key)
        if row is None:
            session.add(event)
            inserted += 1
            continue
        for field in (
            "market",
            "exchange",
            "symbol",
            "ex_dividend_date",
            "record_date",
            "payment_date",
            "amount_per_share",
            "currency",
            "status",
            "source",
            "fetched_at",
        ):
            setattr(row, field, getattr(event, field))
        updated += 1
    session.flush()
    return inserted, updated
