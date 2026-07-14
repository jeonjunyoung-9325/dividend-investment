from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from src.calculations.currency import convert_to_krw
from src.schemas import Market, Position

if TYPE_CHECKING:
    from datetime import datetime

    from src.kis.domestic import DomesticBalanceResult
    from src.kis.overseas import OverseasBalanceResult


def normalize_domestic(result: DomesticBalanceResult, queried_at: datetime) -> tuple[Position, ...]:
    return tuple(
        Position(
            market=Market.DOMESTIC,
            exchange="KRX",
            symbol=item.symbol,
            name=item.name,
            quantity=item.quantity,
            available_quantity=item.available_quantity,
            average_price=item.average_price,
            current_price=item.current_price,
            purchase_amount=item.purchase_amount,
            evaluation_amount=item.evaluation_amount,
            profit_loss=item.profit_loss,
            profit_rate=item.profit_rate,
            currency="KRW",
            krw_exchange_rate=Decimal(1),
            purchase_amount_krw=item.purchase_amount,
            evaluation_amount_krw=item.evaluation_amount,
            profit_loss_krw=item.profit_loss,
            queried_at=queried_at,
            source="KIS domestic balance",
        )
        for item in result.positions
    )


def normalize_overseas(
    result: OverseasBalanceResult,
    queried_at: datetime,
    rates: dict[str, Decimal],
) -> tuple[Position, ...]:
    positions: list[Position] = []
    for item in result.positions:
        rate = rates.get(item.currency)
        positions.append(
            Position(
                market=Market.OVERSEAS,
                exchange=item.exchange,
                symbol=item.symbol,
                name=item.name or item.symbol,
                quantity=item.quantity,
                available_quantity=item.available_quantity,
                average_price=item.average_price,
                current_price=item.current_price,
                purchase_amount=item.purchase_amount,
                evaluation_amount=item.evaluation_amount,
                profit_loss=item.profit_loss,
                profit_rate=item.profit_rate,
                currency=item.currency,
                krw_exchange_rate=rate,
                purchase_amount_krw=_convert(item.purchase_amount, rate),
                evaluation_amount_krw=_convert(item.evaluation_amount, rate),
                profit_loss_krw=_convert(item.profit_loss, rate),
                queried_at=queried_at,
                source="KIS overseas balance",
            )
        )
    return tuple(positions)


def _convert(amount: Decimal, rate: Decimal | None) -> Decimal | None:
    return None if rate is None else convert_to_krw(amount, rate)
