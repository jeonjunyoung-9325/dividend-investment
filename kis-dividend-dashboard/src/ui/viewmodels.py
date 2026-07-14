"""Typed, presentation-only contracts shared by UI data providers."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Literal

import pandas as pd

MetricKind = Literal["actual", "confirmed", "estimated", "neutral"]
SyncState = Literal["success", "partial", "failed", "idle", "running"]


@dataclass(frozen=True, slots=True)
class MetricView:
    """One headline metric card."""

    label: str
    value: str
    delta: str | None = None
    kind: MetricKind = "neutral"
    help_text: str | None = None


@dataclass(frozen=True, slots=True)
class SourceView:
    """Data provenance and freshness metadata."""

    source: str
    as_of: datetime
    fetched_at: datetime
    is_realtime: bool
    using_last_saved: bool = False


@dataclass(frozen=True, slots=True)
class SyncView:
    """Sanitized synchronization outcome safe for display."""

    state: SyncState
    message: str
    last_success_at: datetime | None
    token_action: Literal["reused", "issued", "not_used"]
    inserted: int = 0
    updated: int = 0
    failures: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class DashboardView:
    """Home dashboard presentation dataset."""

    metrics: tuple[MetricView, ...]
    allocation: pd.DataFrame
    position_weights: pd.DataFrame
    dividend_contributions: pd.DataFrame
    monthly_dividends: pd.DataFrame
    asset_history: pd.DataFrame
    cumulative_dividends: pd.DataFrame
    source: SourceView
    sync: SyncView


@dataclass(frozen=True, slots=True)
class PortfolioView:
    """Portfolio table and provenance."""

    positions: pd.DataFrame
    source: SourceView


@dataclass(frozen=True, slots=True)
class DividendView:
    """Actual, confirmed, forecast, and historical dividends."""

    actual: pd.DataFrame
    confirmed: pd.DataFrame
    forecast: pd.DataFrame
    history: pd.DataFrame
    source: SourceView


@dataclass(frozen=True, slots=True)
class CalendarView:
    """Dividend calendar presentation dataset."""

    events: pd.DataFrame
    source: SourceView


@dataclass(frozen=True, slots=True)
class HistoryView:
    """Portfolio snapshot history presentation dataset."""

    snapshots: pd.DataFrame
    source: SourceView


@dataclass(frozen=True, slots=True)
class EditableSettingView:
    """Non-secret settings that the user may change in the UI."""

    display_currency: str
    domestic_tax_rate: Decimal
    us_tax_rate: Decimal
    overseas_tax_rate: Decimal
    enabled_exchanges: tuple[str, ...]
    decimal_places: int
    symbol_overrides: tuple["SymbolForecastOverride", ...] = ()


@dataclass(frozen=True, slots=True)
class SymbolForecastOverride:
    symbol: str
    tax_rate: Decimal | None = None
    forecast_method: str | None = None
    manual_annual_per_share: Decimal | None = None


@dataclass(frozen=True, slots=True)
class ImportColumnMapping:
    """One source-to-target import column mapping."""

    source: str
    target: str


@dataclass(frozen=True, slots=True)
class ImportPreviewView:
    """Validated in-memory import preview."""

    file_hash: str
    detected_encoding: str
    preview: pd.DataFrame
    duplicates: pd.DataFrame
    errors: pd.DataFrame
    detected_mappings: tuple[ImportColumnMapping, ...] = ()


@dataclass(frozen=True, slots=True)
class ImportResultView:
    """Committed import outcome and downloadable error rows."""

    saved: int
    excluded: int
    errors: int
    error_rows_csv: bytes
