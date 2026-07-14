from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import func, select

from src.models import PortfolioSnapshot

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session


def latest_snapshot_at(session: Session) -> datetime | None:
    return session.scalar(select(func.max(PortfolioSnapshot.snapshot_at)))


def list_latest_positions(session: Session) -> tuple[PortfolioSnapshot, ...]:
    latest = latest_snapshot_at(session)
    if latest is None:
        return ()
    statement = (
        select(PortfolioSnapshot)
        .where(PortfolioSnapshot.snapshot_at == latest)
        .order_by(PortfolioSnapshot.market, PortfolioSnapshot.exchange, PortfolioSnapshot.symbol)
    )
    return tuple(session.scalars(statement))
