from __future__ import annotations

from typing import TYPE_CHECKING

from src.repositories.snapshots import upsert_positions

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

    from src.schemas import Position


def save_snapshot(
    session: Session, *, sync_run_id: str, positions: tuple[Position, ...]
) -> tuple[int, int]:
    return upsert_positions(session, sync_run_id=sync_run_id, positions=positions)
