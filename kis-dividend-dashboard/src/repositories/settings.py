from __future__ import annotations

from typing import TYPE_CHECKING, Final

from src.models import AppSetting

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

EDITABLE_KEYS: Final = frozenset(
    {
        "display_currency",
        "domestic_tax_rate",
        "us_tax_rate",
        "overseas_tax_rate",
        "enabled_exchanges",
        "decimal_places",
        "forecast_methods",
        "manual_annual_dividends",
        "symbol_tax_rates",
        "symbol_overrides",
        "investment_rules",
    }
)


def get_setting(session: Session, key: str) -> dict[str, str | int | bool] | None:
    _validate_key(key)
    row = session.get(AppSetting, key)
    return None if row is None else row.value


def set_setting(session: Session, key: str, value: dict[str, str | int | bool]) -> None:
    _validate_key(key)
    row = session.get(AppSetting, key)
    if row is None:
        session.add(AppSetting(key=key, value=value))
    else:
        row.value = value
    session.flush()


def _validate_key(key: str) -> None:
    if key not in EDITABLE_KEYS:
        message = "허용되지 않은 설정 항목입니다."
        raise ValueError(message)
