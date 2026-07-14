from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

from src.kis.dividends import (
    DomesticAccountRightsRequest,
    DomesticDividendScheduleRequest,
    OverseasRightsRequest,
    fetch_domestic_account_rights,
    fetch_domestic_dividend_schedule,
    fetch_overseas_rights,
)
from src.kis.exceptions import KisError
from src.kis.token_io import TokenPolicyError
from src.repositories.dividends import insert_payments, list_events, upsert_events
from src.services.dividend_service import (
    normalize_domestic_schedule,
    normalize_overseas_rights,
    normalize_verified_domestic_payments,
)

if TYPE_CHECKING:
    from datetime import datetime

    from sqlalchemy.orm import Session, sessionmaker

    from src.kis.client import KisClient
    from src.schemas import Position


@dataclass(frozen=True, slots=True)
class DividendSyncRequest:
    account: str
    product_code: str
    positions: tuple[Position, ...]
    now: datetime


def synchronize_dividend_events(
    client: KisClient,
    factory: sessionmaker[Session],
    request: DividendSyncRequest,
) -> tuple[str, int, int, list[str]]:
    start_date = (request.now.date() - timedelta(days=400)).strftime("%Y%m%d")
    end_date = (request.now.date() + timedelta(days=366)).strftime("%Y%m%d")
    inserted = 0
    updated = 0
    succeeded = 0
    failures: list[str] = []
    assets = {(item.market.value, item.exchange, item.symbol) for item in request.positions}
    for market, exchange, symbol in sorted(assets):
        try:
            if market == "domestic":
                source = fetch_domestic_dividend_schedule(
                    client,
                    DomesticDividendScheduleRequest(
                        start_date=start_date,
                        end_date=end_date,
                        symbol=symbol,
                    ),
                )
                events = normalize_domestic_schedule(source, request.now)
            else:
                source = fetch_overseas_rights(
                    client,
                    OverseasRightsRequest(
                        start_date=start_date,
                        end_date=end_date,
                        symbol=symbol,
                    ),
                )
                events = normalize_overseas_rights(
                    source,
                    exchange=exchange,
                    symbol=symbol,
                    fetched_at=request.now,
                )
            with factory() as session, session.begin():
                created, changed = upsert_events(session, events)
            inserted += created
            updated += changed
            succeeded += 1
        except (KisError, TokenPolicyError, ValueError):
            failures.append(f"{symbol} 배당 이력 조회 실패")
    try:
        rights = fetch_domestic_account_rights(
            client,
            DomesticAccountRightsRequest(
                account_no=request.account,
                product_code=request.product_code,
                start_date=(request.now.date() - timedelta(days=730)).strftime("%Y%m%d"),
                end_date=request.now.date().strftime("%Y%m%d"),
            ),
        )
        with factory() as session, session.begin():
            payments = normalize_verified_domestic_payments(
                rights,
                list_events(session),
                as_of=request.now.date(),
            )
            created, excluded = insert_payments(session, payments)
        inserted += created
        updated += excluded
        succeeded += 1
    except (KisError, TokenPolicyError, ValueError):
        failures.append("실제 배당 권리 조회 실패")
    operation_count = len(assets) + 1
    if succeeded == operation_count:
        status = "success"
    elif succeeded:
        status = "partial"
    else:
        status = "failed"
    return status, inserted, updated, failures
