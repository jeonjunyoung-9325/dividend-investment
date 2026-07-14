"""Validated application and external-boundary schemas."""

from datetime import date, datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Market(StrEnum):
    """Supported portfolio market families."""

    DOMESTIC = "domestic"
    OVERSEAS = "overseas"


class DividendStatus(StrEnum):
    """Dividend evidence status."""

    ACTUAL = "actual"
    CONFIRMED = "confirmed"
    ESTIMATED = "estimated"


class Position(BaseModel):
    """Normalized balance position with original and KRW values."""

    model_config = ConfigDict(frozen=True)

    market: Market
    exchange: str
    symbol: str
    name: str
    quantity: Decimal = Field(ge=0)
    available_quantity: Decimal | None = Field(default=None, ge=0)
    average_price: Decimal | None = Field(default=None, ge=0)
    current_price: Decimal | None = Field(default=None, ge=0)
    purchase_amount: Decimal | None = Field(default=None, ge=0)
    evaluation_amount: Decimal | None = None
    profit_loss: Decimal | None = None
    profit_rate: Decimal | None = None
    currency: str = Field(min_length=3, max_length=3)
    krw_exchange_rate: Decimal | None = Field(default=None, gt=0)
    purchase_amount_krw: Decimal | None = None
    evaluation_amount_krw: Decimal | None = None
    profit_loss_krw: Decimal | None = None
    queried_at: datetime
    source: str

    @property
    def natural_key(self) -> tuple[str, str, str]:
        """Keep identical tickers on distinct exchanges separate."""
        return self.market.value, self.exchange, self.symbol


class DividendHistoryItem(BaseModel):
    """Per-share dividend observation used by forecasts."""

    model_config = ConfigDict(frozen=True)

    payment_date: date
    amount_per_share: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    source: str


class DividendPaymentInput(BaseModel):
    """Normalized actual dividend row parsed from a user file."""

    model_config = ConfigDict(frozen=True)

    market: Market
    exchange: str
    symbol: str
    name: str
    payment_date: date
    gross_amount: Decimal = Field(ge=0)
    tax_amount: Decimal = Field(ge=0)
    net_amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)
    quantity_at_record_date: Decimal | None = Field(default=None, ge=0)
    amount_per_share: Decimal | None = Field(default=None, ge=0)
    krw_exchange_rate: Decimal | None = Field(default=None, gt=0)
    source: str = "user_upload"
    import_hash: str


class ExchangeRateQuote(BaseModel):
    """Rate plus evidence metadata displayed to the user."""

    model_config = ConfigDict(frozen=True)

    base_currency: str
    quote_currency: str
    rate: Decimal = Field(gt=0)
    rate_date: date
    fetched_at: datetime
    source: str
    is_realtime: bool
    is_last_known: bool = False
