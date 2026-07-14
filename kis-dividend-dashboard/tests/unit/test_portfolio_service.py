from datetime import UTC, datetime
from decimal import Decimal

from src.kis.ministock import MiniStockBalanceResult, MiniStockPosition
from src.schemas import Market, Position
from src.services.portfolio_service import merge_overseas_positions, normalize_ministock

NOW = datetime(2026, 7, 15, tzinfo=UTC)


def test_ministock_position_is_normalized_with_official_exchange_rate() -> None:
    # Given
    result = MiniStockBalanceResult(
        positions=(
            MiniStockPosition(
                exchange="AMEX",
                symbol="SCHD",
                name="Schwab ETF",
                quantity=Decimal("0.125"),
                available_quantity=Decimal("0.125"),
                average_price=Decimal(70),
                current_price=Decimal(75),
                purchase_amount=Decimal("8.75"),
                evaluation_amount=Decimal("9.375"),
                profit_loss=Decimal("0.625"),
                profit_rate=Decimal("7.142857"),
                currency="USD",
                exchange_rate=Decimal(1500),
            ),
        )
    )

    # When
    position = normalize_ministock(result, NOW)[0]

    # Then
    assert position.quantity == Decimal("0.125")
    assert position.evaluation_amount_krw == Decimal("14062.500")
    assert position.source == "KIS MiniStock balance"


def test_regular_and_ministock_same_symbol_are_combined_without_overwrite() -> None:
    # Given
    regular = _position(quantity="2", purchase="140", evaluation="150", source="regular")
    ministock = _position(quantity="0.5", purchase="36", evaluation="38", source="ministock")

    # When
    merged = merge_overseas_positions((regular,), (ministock,))

    # Then
    assert len(merged) == 1
    assert merged[0].quantity == Decimal("2.5")
    assert merged[0].purchase_amount == Decimal(176)
    assert merged[0].evaluation_amount == Decimal(188)
    assert merged[0].average_price == Decimal("70.4")
    assert merged[0].source == "KIS overseas + MiniStock balance"


def _position(*, quantity: str, purchase: str, evaluation: str, source: str) -> Position:
    purchase_value = Decimal(purchase)
    evaluation_value = Decimal(evaluation)
    rate = Decimal(1500)
    return Position(
        market=Market.OVERSEAS,
        exchange="AMEX",
        symbol="SCHD",
        name="Schwab ETF",
        quantity=Decimal(quantity),
        available_quantity=Decimal(quantity),
        average_price=purchase_value / Decimal(quantity),
        current_price=Decimal(75),
        purchase_amount=purchase_value,
        evaluation_amount=evaluation_value,
        profit_loss=evaluation_value - purchase_value,
        profit_rate=(evaluation_value - purchase_value) / purchase_value * Decimal(100),
        currency="USD",
        krw_exchange_rate=rate,
        purchase_amount_krw=purchase_value * rate,
        evaluation_amount_krw=evaluation_value * rate,
        profit_loss_krw=(evaluation_value - purchase_value) * rate,
        queried_at=NOW,
        source=source,
    )
