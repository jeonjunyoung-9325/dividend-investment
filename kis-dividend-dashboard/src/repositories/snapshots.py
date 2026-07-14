from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import case, func, select

from src.models import PortfolioSnapshot

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session

    from src.schemas import Position


def upsert_positions(
    session: Session,
    *,
    sync_run_id: str,
    positions: tuple[Position, ...],
) -> tuple[int, int]:
    existing = {
        (row.market, row.exchange, row.symbol): row
        for row in session.scalars(
            select(PortfolioSnapshot).where(PortfolioSnapshot.sync_run_id == sync_run_id)
        )
    }
    inserted = 0
    updated = 0
    for position in positions:
        key = position.natural_key
        values = _values(position)
        row = existing.get(key)
        if row is None:
            row = PortfolioSnapshot(sync_run_id=sync_run_id, **values)
            session.add(row)
            existing[key] = row
            inserted += 1
            continue
        for field, value in values.items():
            setattr(row, field, value)
        updated += 1
    session.flush()
    return inserted, updated


def asset_history(
    session: Session, *, start_at: datetime | None = None
) -> tuple[tuple[datetime, Decimal, Decimal, Decimal], ...]:
    amount = func.coalesce(PortfolioSnapshot.evaluation_amount_krw, Decimal(0))
    domestic = func.sum(case((PortfolioSnapshot.market == "domestic", amount), else_=Decimal(0)))
    overseas = func.sum(case((PortfolioSnapshot.market == "overseas", amount), else_=Decimal(0)))
    statement = select(
        PortfolioSnapshot.snapshot_at,
        func.sum(amount),
        domestic,
        overseas,
    ).group_by(PortfolioSnapshot.snapshot_at)
    if start_at is not None:
        statement = statement.where(PortfolioSnapshot.snapshot_at >= start_at)
    statement = statement.order_by(PortfolioSnapshot.snapshot_at)
    return tuple(session.execute(statement).tuples())


def _values(position: Position) -> dict[str, object]:
    return {
        "snapshot_at": position.queried_at,
        "market": position.market.value,
        "exchange": position.exchange,
        "symbol": position.symbol,
        "name": position.name,
        "quantity": position.quantity,
        "available_quantity": position.available_quantity,
        "average_price": position.average_price,
        "current_price": position.current_price,
        "purchase_amount": position.purchase_amount,
        "evaluation_amount": position.evaluation_amount,
        "profit_loss": position.profit_loss,
        "profit_rate": position.profit_rate,
        "currency": position.currency,
        "krw_exchange_rate": position.krw_exchange_rate,
        "purchase_amount_krw": position.purchase_amount_krw,
        "evaluation_amount_krw": position.evaluation_amount_krw,
        "profit_loss_krw": position.profit_loss_krw,
        "source": position.source,
    }
