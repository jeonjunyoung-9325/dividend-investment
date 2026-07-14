"""SQLAlchemy 2.x models for portfolio, dividends, rates, synchronization, and tokens."""

from __future__ import annotations

from datetime import date, datetime  # noqa: TC003
from decimal import Decimal  # noqa: TC003
from uuid import uuid4

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import JSON

MONEY = Numeric(28, 8)
RATE = Numeric(24, 10)
PERCENT = Numeric(18, 8)


def new_id() -> str:
    """Return a cross-dialect UUID identifier."""
    return str(uuid4())


class Base(DeclarativeBase):
    """Declarative model registry."""


class TimestampMixin:
    """Database-maintained audit timestamps."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class SyncRun(Base):
    """One end-to-end synchronization attempt."""

    __tablename__ = "sync_runs"
    __table_args__ = (
        CheckConstraint("records_inserted >= 0", name="ck_sync_runs_inserted_nonnegative"),
        CheckConstraint("records_updated >= 0", name="ck_sync_runs_updated_nonnegative"),
        Index("ix_sync_runs_started_at", "started_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    domestic_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    overseas_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    dividend_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    exchange_rate_status: Mapped[str] = mapped_column(String(24), nullable=False, default="pending")
    message: Mapped[str | None] = mapped_column(Text)
    records_inserted: Mapped[int] = mapped_column(default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class PortfolioSnapshot(Base):
    """A normalized holding captured during a synchronization run."""

    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint(
            "sync_run_id", "market", "exchange", "symbol", name="uq_snapshot_run_asset"
        ),
        CheckConstraint("quantity >= 0", name="ck_snapshot_quantity_nonnegative"),
        CheckConstraint(
            "krw_exchange_rate IS NULL OR krw_exchange_rate > 0", name="ck_snapshot_fx_positive"
        ),
        Index("ix_snapshots_asset_time", "market", "exchange", "symbol", "snapshot_at"),
        Index("ix_snapshots_time", "snapshot_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    sync_run_id: Mapped[str] = mapped_column(ForeignKey("sync_runs.id"), nullable=False)
    snapshot_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    quantity: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    available_quantity: Mapped[Decimal | None] = mapped_column(MONEY)
    average_price: Mapped[Decimal | None] = mapped_column(MONEY)
    current_price: Mapped[Decimal | None] = mapped_column(MONEY)
    purchase_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    evaluation_amount: Mapped[Decimal | None] = mapped_column(MONEY)
    profit_loss: Mapped[Decimal | None] = mapped_column(MONEY)
    profit_rate: Mapped[Decimal | None] = mapped_column(PERCENT)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    krw_exchange_rate: Mapped[Decimal | None] = mapped_column(RATE)
    purchase_amount_krw: Mapped[Decimal | None] = mapped_column(MONEY)
    evaluation_amount_krw: Mapped[Decimal | None] = mapped_column(MONEY)
    profit_loss_krw: Mapped[Decimal | None] = mapped_column(MONEY)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class DividendPayment(Base, TimestampMixin):
    """An actual dividend credited to the account."""

    __tablename__ = "dividend_payments"
    __table_args__ = (
        CheckConstraint(
            "gross_amount >= 0 AND tax_amount >= 0 AND net_amount >= 0",
            name="ck_payment_amounts_nonnegative",
        ),
        Index("ix_dividend_payments_payment_date", "payment_date"),
        Index("ix_dividend_payments_asset_date", "market", "exchange", "symbol", "payment_date"),
        Index(
            "uq_dividend_payment_external",
            "source",
            "external_id",
            unique=True,
            postgresql_where=text("external_id IS NOT NULL"),
        ),
        Index(
            "uq_dividend_payment_import_hash",
            "import_hash",
            unique=True,
            postgresql_where=text("import_hash IS NOT NULL"),
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    ex_dividend_date: Mapped[date | None] = mapped_column(Date)
    record_date: Mapped[date | None] = mapped_column(Date)
    payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    quantity_at_record_date: Mapped[Decimal | None] = mapped_column(MONEY)
    gross_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    tax_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    net_amount: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    amount_per_share: Mapped[Decimal | None] = mapped_column(MONEY)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    krw_exchange_rate: Mapped[Decimal | None] = mapped_column(RATE)
    gross_amount_krw: Mapped[Decimal | None] = mapped_column(MONEY)
    tax_amount_krw: Mapped[Decimal | None] = mapped_column(MONEY)
    net_amount_krw: Mapped[Decimal | None] = mapped_column(MONEY)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    external_id: Mapped[str | None] = mapped_column(String(160))
    import_hash: Mapped[str | None] = mapped_column(String(64))
    memo: Mapped[str | None] = mapped_column(Text)


class DividendEvent(Base, TimestampMixin):
    """Published or historical per-share dividend evidence."""

    __tablename__ = "dividend_events"
    __table_args__ = (
        UniqueConstraint("event_key", name="uq_dividend_event_key"),
        CheckConstraint("amount_per_share >= 0", name="ck_event_amount_nonnegative"),
        Index("ix_dividend_events_asset_date", "market", "exchange", "symbol", "payment_date"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    event_key: Mapped[str] = mapped_column(String(64), nullable=False)
    market: Mapped[str] = mapped_column(String(16), nullable=False)
    exchange: Mapped[str] = mapped_column(String(16), nullable=False, default="")
    symbol: Mapped[str] = mapped_column(String(32), nullable=False)
    ex_dividend_date: Mapped[date | None] = mapped_column(Date)
    record_date: Mapped[date | None] = mapped_column(Date)
    payment_date: Mapped[date | None] = mapped_column(Date)
    amount_per_share: Mapped[Decimal] = mapped_column(MONEY, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ExchangeRate(Base):
    """A dated exchange-rate observation with source metadata."""

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint(
            "rate_date",
            "base_currency",
            "quote_currency",
            "source",
            name="uq_exchange_rate_observation",
        ),
        CheckConstraint("rate > 0", name="ck_exchange_rate_positive"),
        CheckConstraint(
            "base_currency <> quote_currency", name="ck_exchange_rate_distinct_currencies"
        ),
        Index(
            "ix_exchange_rates_lookup", "base_currency", "quote_currency", "rate_date", "fetched_at"
        ),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    rate_date: Mapped[date] = mapped_column(Date, nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    rate: Mapped[Decimal] = mapped_column(RATE, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class KisTokenCache(Base, TimestampMixin):
    """Encrypted persistent token and non-sensitive issuance state."""

    __tablename__ = "kis_token_cache"
    __table_args__ = (
        UniqueConstraint("environment", "app_key_fingerprint", name="uq_kis_token_identity"),
        CheckConstraint("environment IN ('real', 'demo')", name="ck_kis_token_environment"),
        CheckConstraint(
            "state IN ('empty','requesting','usable','decrypt_failed','request_failed','revoked')",
            name="ck_kis_token_state",
        ),
        CheckConstraint(
            "expires_at IS NULL OR issued_at IS NULL OR expires_at > issued_at",
            name="ck_kis_token_expiry_order",
        ),
        Index("ix_kis_token_cache_state_expiry", "state", "expires_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    environment: Mapped[str] = mapped_column(String(8), nullable=False)
    app_key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    encrypted_access_token: Mapped[bytes | None] = mapped_column(LargeBinary)
    token_type: Mapped[str | None] = mapped_column(String(24))
    issued_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    state: Mapped[str] = mapped_column(String(24), nullable=False, default="empty")
    request_lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    blocked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_failure_kind: Mapped[str | None] = mapped_column(String(40))
    last_failure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AppSetting(Base):
    """A typed-at-service-boundary application setting."""

    __tablename__ = "app_settings"

    key: Mapped[str] = mapped_column(String(160), primary_key=True)
    value: Mapped[dict[str, str | int | bool]] = mapped_column(
        JSON().with_variant(JSONB(), "postgresql"), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
