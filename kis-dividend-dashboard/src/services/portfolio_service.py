from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING

from src.calculations.currency import convert_to_krw
from src.schemas import Market, Position

if TYPE_CHECKING:
    from datetime import datetime

    from src.kis.domestic import DomesticBalanceResult
    from src.kis.ministock import MiniStockBalanceResult
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


def normalize_ministock(
    result: MiniStockBalanceResult,
    queried_at: datetime,
) -> tuple[Position, ...]:
    return tuple(
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
            krw_exchange_rate=item.exchange_rate,
            purchase_amount_krw=_convert(item.purchase_amount, item.exchange_rate),
            evaluation_amount_krw=_convert(item.evaluation_amount, item.exchange_rate),
            profit_loss_krw=_convert(item.profit_loss, item.exchange_rate),
            queried_at=queried_at,
            source="KIS MiniStock balance",
        )
        for item in result.positions
    )


def merge_overseas_positions(
    regular: tuple[Position, ...],
    ministock: tuple[Position, ...],
) -> tuple[Position, ...]:
    merged = {position.natural_key: position for position in regular}
    for position in ministock:
        existing = merged.get(position.natural_key)
        merged[position.natural_key] = (
            position if existing is None else _merge_position(existing, position)
        )
    return tuple(merged.values())


def _merge_position(regular: Position, ministock: Position) -> Position:
    quantity = regular.quantity + ministock.quantity
    purchase = _sum_amount(regular.purchase_amount, ministock.purchase_amount)
    evaluation = _sum_amount(regular.evaluation_amount, ministock.evaluation_amount)
    profit = _sum_amount(regular.profit_loss, ministock.profit_loss)
    rate = ministock.krw_exchange_rate or regular.krw_exchange_rate
    return regular.model_copy(
        update={
            "quantity": quantity,
            "available_quantity": _sum_amount(
                regular.available_quantity, ministock.available_quantity
            ),
            "average_price": None if purchase is None or not quantity else purchase / quantity,
            "current_price": ministock.current_price or regular.current_price,
            "purchase_amount": purchase,
            "evaluation_amount": evaluation,
            "profit_loss": profit,
            "profit_rate": (
                None
                if purchase is None or profit is None or not purchase
                else profit / purchase * Decimal(100)
            ),
            "krw_exchange_rate": rate,
            "purchase_amount_krw": None if purchase is None else _convert(purchase, rate),
            "evaluation_amount_krw": None if evaluation is None else _convert(evaluation, rate),
            "profit_loss_krw": None if profit is None else _convert(profit, rate),
            "queried_at": max(regular.queried_at, ministock.queried_at),
            "source": "KIS overseas + MiniStock balance",
        }
    )


def _sum_amount(left: Decimal | None, right: Decimal | None) -> Decimal | None:
    if left is None:
        return right
    if right is None:
        return left
    return left + right


def _convert(amount: Decimal, rate: Decimal | None) -> Decimal | None:
    return None if rate is None else convert_to_krw(amount, rate)
