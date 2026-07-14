from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import BytesIO
from typing import Final

import pandas as pd

from src.config import get_settings
from src.repositories.dividends import existing_import_hashes, insert_payments
from src.schemas import DividendPaymentInput, Market
from src.services.ui_read_service import session_factory
from src.ui.viewmodels import ImportColumnMapping, ImportPreviewView, ImportResultView

COLUMN_ALIASES: Final[dict[str, tuple[str, ...]]] = {
    "symbol": ("종목코드", "티커", "symbol", "ticker"),
    "name": ("종목명", "name"),
    "payment_date": ("지급일", "거래일", "payment_date"),
    "gross_amount": ("세전 배당금", "배당금", "외화 배당금", "gross_amount"),
    "tax_amount": ("세금", "제세금", "tax_amount"),
    "net_amount": ("실수령액", "net_amount"),
    "currency": ("통화", "currency"),
    "exchange": ("거래소", "exchange"),
    "quantity_at_record_date": ("수량", "quantity"),
    "amount_per_share": ("주당배당금", "amount_per_share"),
    "krw_exchange_rate": ("환율", "exchange_rate"),
}


@dataclass(frozen=True, slots=True)
class ImportErrorRow:
    row_number: int
    errors: tuple["FieldError", ...]
    raw: dict[str, str]

    @property
    def reason(self) -> str:
        return "; ".join(error.message for error in self.errors)


@dataclass(frozen=True, slots=True)
class FieldError:
    field: str
    message: str


@dataclass(frozen=True, slots=True)
class ImportPreview:
    file_hash: str
    detected_encoding: str | None
    column_mapping: dict[str, str]
    valid_rows: tuple[DividendPaymentInput, ...]
    errors: tuple[ImportErrorRow, ...]

    @property
    def error_rows(self) -> tuple[ImportErrorRow, ...]:
        return self.errors


def read_uploaded_table(content: bytes, filename: str) -> tuple[pd.DataFrame, str | None]:
    lower = filename.lower()
    if lower.endswith(".xlsx"):
        return pd.read_excel(BytesIO(content), engine="openpyxl", dtype=str), None
    if not lower.endswith(".csv"):
        msg = "CSV 또는 XLSX 파일만 업로드할 수 있습니다."
        raise ValueError(msg)
    for encoding in ("utf-8-sig", "utf-8", "cp949"):
        try:
            return pd.read_csv(BytesIO(content), encoding=encoding, dtype=str), encoding
        except UnicodeDecodeError:
            continue
    msg = "지원하는 인코딩(UTF-8, UTF-8-SIG, CP949)으로 읽을 수 없습니다."
    raise UnicodeError(msg)


def detect_columns(columns: list[str]) -> dict[str, str]:
    normalized = {str(column).strip().lower(): str(column) for column in columns}
    detected: dict[str, str] = {}
    for field, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            found = normalized.get(alias.lower())
            if found is not None:
                detected[field] = found
                break
    return detected


def preview_import(
    content: bytes,
    filename: str,
    user_mapping: dict[str, str] | None = None,
    *,
    source: str = "user_upload",
) -> ImportPreview:
    frame, encoding = read_uploaded_table(content, filename)
    mapping = detect_columns([str(column) for column in frame.columns])
    mapping.update(user_mapping or {})
    required = {"symbol", "payment_date", "gross_amount", "currency"}
    missing = sorted(required - mapping.keys())
    if missing:
        msg = f"필수 컬럼 매핑이 없습니다: {', '.join(missing)}"
        raise ValueError(msg)
    valid: list[DividendPaymentInput] = []
    errors: list[ImportErrorRow] = []
    for offset, (_, row) in enumerate(frame.iterrows(), start=2):
        raw = {str(key): "" if pd.isna(value) else str(value) for key, value in row.items()}
        row_errors = _validate_row(raw, mapping)
        if row_errors:
            errors.append(ImportErrorRow(offset, row_errors, raw))
            continue
        valid.append(_parse_row(raw, mapping, source=source))
    return ImportPreview(
        sha256(content).hexdigest(), encoding, mapping, tuple(valid), tuple(errors)
    )


def parse_decimal(raw: str) -> Decimal:
    value = raw.strip().replace(",", "").replace("₩", "").replace("$", "").replace("¥", "")
    if value.startswith("(") and value.endswith(")"):
        value = f"-{value[1:-1]}"
    return Decimal(value or "0")


def parse_date(raw: str) -> date:
    text = raw.strip()
    for pattern in ("%Y-%m-%d", "%Y.%m.%d", "%Y/%m/%d", "%Y%m%d"):
        try:
            return datetime.strptime(text, pattern).date()
        except ValueError:
            continue
    msg = f"날짜 형식을 확인해 주세요: {text}"
    raise ValueError(msg)


def row_import_hash(values: dict[str, str]) -> str:
    canonical = "|".join(f"{key}={values[key].strip()}" for key in sorted(values))
    return sha256(canonical.encode("utf-8")).hexdigest()


def build_import_hash(values: Mapping[str, str | date | Decimal]) -> str:
    normalized: dict[str, str] = {}
    for key, value in values.items():
        if isinstance(value, Decimal):
            normalized[key] = format(value.normalize(), "f")
        elif isinstance(value, date):
            normalized[key] = value.isoformat()
        else:
            normalized[key] = str(value).strip().upper()
    return row_import_hash(normalized)


def parse_dividend_file(filename: str, content: bytes) -> ImportPreview:
    return preview_import(content, filename)


def errors_to_csv(errors: tuple[ImportErrorRow, ...]) -> bytes:
    rows = [{"행": item.row_number, "오류": item.reason, **item.raw} for item in errors]
    return pd.DataFrame(rows).to_csv(index=False).encode("utf-8-sig")


def preview_dividend_import(filename: str, content: bytes) -> ImportPreviewView:
    parsed = preview_import(content, filename)
    frame, _ = read_uploaded_table(content, filename)
    hashes = {row.import_hash for row in parsed.valid_rows}
    duplicates: set[str] = set()
    if not get_settings().DEMO_MODE:
        with session_factory()() as session:
            duplicates = existing_import_hashes(session, hashes)
    duplicate_frame = pd.DataFrame(
        [row.model_dump() for row in parsed.valid_rows if row.import_hash in duplicates]
    )
    error_frame = pd.DataFrame(
        [{"행": item.row_number, "오류": item.reason, **item.raw} for item in parsed.errors]
    )
    return ImportPreviewView(
        parsed.file_hash,
        parsed.detected_encoding or "XLSX",
        frame,
        duplicate_frame,
        error_frame,
        tuple(
            ImportColumnMapping(source=source, target=target)
            for target, source in parsed.column_mapping.items()
        ),
    )


def commit_dividend_import(
    filename: str,
    content: bytes,
    mappings: tuple[ImportColumnMapping, ...],
    *,
    source: str = "user_upload",
) -> ImportResultView:
    user_mapping = {
        item.target: item.source
        for item in mappings
        if item.target not in {"", "사용 안 함", "quantity"}
    }
    if any(item.target == "quantity" for item in mappings):
        quantity_source = next(item.source for item in mappings if item.target == "quantity")
        user_mapping["quantity_at_record_date"] = quantity_source
    parsed = preview_import(content, filename, user_mapping, source=source)
    if get_settings().DEMO_MODE:
        return ImportResultView(
            0, len(parsed.valid_rows), len(parsed.errors), errors_to_csv(parsed.errors)
        )
    with session_factory()() as session, session.begin():
        inserted, excluded = insert_payments(session, parsed.valid_rows)
    return ImportResultView(inserted, excluded, len(parsed.errors), errors_to_csv(parsed.errors))


def _parse_row(
    raw: dict[str, str], mapping: dict[str, str], *, source: str
) -> DividendPaymentInput:
    symbol = raw[mapping["symbol"]].strip().upper()
    if not symbol:
        msg = "종목코드 또는 티커가 없습니다."
        raise ValueError(msg)
    exchange = raw.get(mapping.get("exchange", ""), "KRX").strip() or "KRX"
    currency = raw[mapping["currency"]].strip().upper()
    gross = parse_decimal(raw[mapping["gross_amount"]])
    tax = parse_decimal(raw[mapping["tax_amount"]]) if "tax_amount" in mapping else Decimal(0)
    net = parse_decimal(raw[mapping["net_amount"]]) if "net_amount" in mapping else gross - tax
    normalized = {
        "exchange": exchange,
        "symbol": symbol,
        "payment_date": parse_date(raw[mapping["payment_date"]]).isoformat(),
        "gross_amount": str(gross),
        "tax_amount": str(tax),
        "net_amount": str(net),
        "currency": currency,
    }
    return DividendPaymentInput(
        market=Market.DOMESTIC if exchange == "KRX" else Market.OVERSEAS,
        exchange=exchange,
        symbol=symbol,
        name=raw.get(mapping.get("name", ""), symbol).strip() or symbol,
        payment_date=date.fromisoformat(normalized["payment_date"]),
        gross_amount=Decimal(normalized["gross_amount"]),
        tax_amount=Decimal(normalized["tax_amount"]),
        net_amount=Decimal(normalized["net_amount"]),
        currency=currency,
        quantity_at_record_date=_optional_decimal(raw, mapping, "quantity_at_record_date"),
        amount_per_share=_optional_decimal(raw, mapping, "amount_per_share"),
        krw_exchange_rate=_optional_decimal(raw, mapping, "krw_exchange_rate"),
        source=source,
        import_hash=row_import_hash(normalized),
    )


def _optional_decimal(raw: dict[str, str], mapping: dict[str, str], field: str) -> Decimal | None:
    column = mapping.get(field)
    if column is None or not raw.get(column, "").strip():
        return None
    return parse_decimal(raw[column])


def _validate_row(raw: dict[str, str], mapping: dict[str, str]) -> tuple[FieldError, ...]:
    errors: list[FieldError] = []
    symbol = raw[mapping["symbol"]].strip()
    if not symbol:
        errors.append(FieldError("symbol", "종목코드 또는 티커가 없습니다."))
    try:
        parse_date(raw[mapping["payment_date"]])
    except ValueError as error:
        errors.append(FieldError("payment_date", str(error)))
    try:
        parse_decimal(raw[mapping["gross_amount"]])
    except InvalidOperation:
        errors.append(FieldError("gross_amount", "금액 형식을 확인해 주세요."))
    return tuple(errors)
