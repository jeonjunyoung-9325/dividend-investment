from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from src.kis.client import KisEnvironment
from src.kis.exceptions import KisError
from src.kis.ministock import MiniStockBalanceRequest, fetch_ministock_balance
from src.kis.overseas import OverseasBalanceRequest, OverseasExchange, fetch_overseas_balance
from src.kis.token_io import TokenPolicyError
from src.repositories.settings import get_setting
from src.services.exchange_rate_service import rate_for_currency
from src.services.portfolio_service import (
    merge_overseas_positions,
    normalize_ministock,
    normalize_overseas,
)

if TYPE_CHECKING:
    from datetime import datetime
    from decimal import Decimal

    from sqlalchemy.orm import Session

    from src.kis.client import KisClient
    from src.schemas import Position

CURRENCY_BY_EXCHANGE = {
    "NASD": "USD",
    "NAS": "USD",
    "NYSE": "USD",
    "AMEX": "USD",
    "SEHK": "HKD",
    "SHAA": "CNY",
    "SZAA": "CNY",
    "TKSE": "JPY",
    "HASE": "VND",
    "VNSE": "VND",
}


@dataclass(frozen=True, slots=True)
class OverseasSyncRequest:
    account: str
    product_code: str
    exchanges: tuple[str, ...]
    rates: dict[str, Decimal]
    now: datetime


def fetch_overseas_positions(
    client: KisClient,
    request: OverseasSyncRequest,
) -> tuple[str, tuple[Position, ...], list[str]]:
    regular: list[Position] = []
    ministock: tuple[Position, ...] = ()
    failures: list[str] = []
    successful_queries = 0
    for exchange in request.exchanges:
        try:
            result = fetch_overseas_balance(
                client,
                OverseasBalanceRequest(
                    account_no=request.account,
                    product_code=request.product_code,
                    exchange=OverseasExchange(exchange),
                    currency=CURRENCY_BY_EXCHANGE[exchange],
                ),
            )
            regular.extend(normalize_overseas(result, request.now, request.rates))
            successful_queries += 1
        except (KisError, TokenPolicyError, ValueError):
            failures.append(f"해외 거래소 {exchange} 잔고 조회 실패")

    if client.environment is KisEnvironment.REAL:
        try:
            result = fetch_ministock_balance(
                client,
                MiniStockBalanceRequest(
                    account_no=request.account,
                    product_code=request.product_code,
                ),
            )
            ministock = normalize_ministock(result, request.now)
            successful_queries += 1
        except (KisError, TokenPolicyError, ValueError):
            failures.append("미니스탁 잔고 조회 실패")

    positions = merge_overseas_positions(tuple(regular), ministock)
    if successful_queries and failures:
        status = "partial"
    elif successful_queries or (
        not request.exchanges and client.environment is KisEnvironment.DEMO
    ):
        status = "success"
    else:
        status = "failed"
    return status, positions, failures


def enabled_exchanges(session: Session) -> tuple[str, ...]:
    stored = get_setting(session, "enabled_exchanges")
    raw = "NASD" if stored is None else str(stored.get("value", "NASD"))
    return tuple(item for item in raw.split(",") if item in CURRENCY_BY_EXCHANGE)


def rates_for_exchanges(
    session: Session,
    exchanges: tuple[str, ...],
    default_usd: Decimal,
    now: datetime,
) -> dict[str, Decimal]:
    rates: dict[str, Decimal] = {}
    for currency in {CURRENCY_BY_EXCHANGE[item] for item in exchanges}:
        quote = rate_for_currency(session, currency, default_usd_krw=default_usd, now=now)
        if quote is not None:
            rates[currency] = quote.rate
    return rates
