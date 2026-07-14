from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from hashlib import sha256
from typing import TYPE_CHECKING

from src.models import DividendEvent
from src.schemas import DividendPaymentInput, Market

if TYPE_CHECKING:
    from src.kis.dividends import (
        DomesticAccountRightApi,
        DomesticDividendSchedule,
        OverseasRightApi,
    )

COMPACT_DATE_LENGTH = 8


def normalize_domestic_schedule(
    events: tuple[DomesticDividendSchedule, ...], fetched_at: datetime
) -> tuple[DividendEvent, ...]:
    normalized: list[DividendEvent] = []
    for event in events:
        record_date = _date_or_none(event.record_date)
        payment_date = _date_or_none(event.payment_date)
        identity = "|".join(
            (
                "domestic",
                "KRX",
                event.symbol,
                event.record_date,
                event.payment_date,
                str(event.amount_per_share),
            )
        )
        normalized.append(
            DividendEvent(
                event_key=sha256(identity.encode()).hexdigest(),
                market="domestic",
                exchange="KRX",
                symbol=event.symbol,
                record_date=record_date,
                payment_date=payment_date,
                amount_per_share=event.amount_per_share,
                currency="KRW",
                status="announced_unverified",
                source="KIS domestic dividend schedule",
                fetched_at=fetched_at,
            )
        )
    return tuple(normalized)


def normalize_overseas_rights(
    rights: tuple[OverseasRightApi, ...],
    *,
    exchange: str,
    symbol: str,
    fetched_at: datetime,
) -> tuple[DividendEvent, ...]:
    normalized: list[DividendEvent] = []
    expected_symbol = symbol.strip().upper()
    for right in rights:
        if right.pdno.strip().upper() != expected_symbol:
            continue
        amount, currency = _overseas_amount(right)
        record_date = _date_or_none(right.acpl_bass_dt)
        if amount is None or record_date is None:
            continue
        identity = "|".join(
            (
                "overseas",
                exchange,
                expected_symbol,
                record_date.isoformat(),
                str(amount),
                currency,
            )
        )
        normalized.append(
            DividendEvent(
                event_key=sha256(identity.encode()).hexdigest(),
                market="overseas",
                exchange=exchange,
                symbol=expected_symbol,
                record_date=record_date,
                amount_per_share=amount,
                currency=currency,
                status="confirmed" if right.dfnt_yn == "Y" else "announced_unverified",
                source="KIS overseas dividend rights",
                fetched_at=fetched_at,
            )
        )
    return tuple(normalized)


def normalize_verified_domestic_payments(
    rights: tuple[DomesticAccountRightApi, ...],
    events: tuple[DividendEvent, ...],
    *,
    as_of: date,
) -> tuple[DividendPaymentInput, ...]:
    indexed = {
        (event.symbol, event.record_date, event.payment_date, event.amount_per_share)
        for event in events
        if event.market == "domestic"
    }
    payments: list[DividendPaymentInput] = []
    for right in rights:
        record_date = _date_or_none(right.bass_dt)
        payment_date = _date_or_none(right.cash_dfrm_dt)
        if (
            record_date is None
            or payment_date is None
            or payment_date > as_of
            or right.cblc_qty <= 0
            or right.last_alct_amt <= 0
            or right.tax_amt != 0
        ):
            continue
        symbol = right.shtn_pdno.strip() or right.pdno[-6:]
        amount_per_share = right.last_alct_amt / right.cblc_qty
        if (symbol, record_date, payment_date, amount_per_share) not in indexed:
            continue
        identity = "|".join(
            (
                "KIS account rights",
                symbol,
                record_date.isoformat(),
                payment_date.isoformat(),
                str(right.cblc_qty),
                str(right.last_alct_amt),
            )
        )
        payments.append(
            DividendPaymentInput(
                market=Market.DOMESTIC,
                exchange="KRX",
                symbol=symbol,
                name=right.prdt_name,
                payment_date=payment_date,
                gross_amount=right.last_alct_amt,
                tax_amount=Decimal(0),
                net_amount=right.last_alct_amt,
                currency="KRW",
                quantity_at_record_date=right.cblc_qty,
                amount_per_share=amount_per_share,
                krw_exchange_rate=Decimal(1),
                source="KIS 계좌 권리·배당일정 대조",
                import_hash=sha256(identity.encode()).hexdigest(),
            )
        )
    return tuple(payments)


def _overseas_amount(right: OverseasRightApi) -> tuple[Decimal | None, str]:
    candidates = (
        (right.alct_frcr_unpr, right.crcy_cd),
        (right.stkp_dvdn_frcr_amt2, right.crcy_cd2),
        (right.stkp_dvdn_frcr_amt3, right.crcy_cd3),
        (right.stkp_dvdn_frcr_amt4, right.crcy_cd4),
    )
    for amount, currency in candidates:
        if amount > 0 and currency:
            return amount, currency
    return None, ""


def _date_or_none(value: str) -> date | None:
    normalized = value.strip().replace("-", "").replace("/", "")
    if not normalized or len(normalized) != COMPACT_DATE_LENGTH:
        return None
    try:
        return date(int(normalized[:4]), int(normalized[4:6]), int(normalized[6:]))
    except ValueError:
        return None
