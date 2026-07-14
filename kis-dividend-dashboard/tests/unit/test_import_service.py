from datetime import date
from decimal import Decimal
from hashlib import sha256
from io import BytesIO

import pytest
from openpyxl import Workbook
from src.services.import_service import build_import_hash, parse_dividend_file

CSV_TEXT = (
    "종목코드,종목명,지급일,세전 배당금,세금,실수령액,통화\n"
    "005930,삼성전자,2026-04-20,10,1.54,8.46,KRW\n"
)


@pytest.mark.parametrize("encoding", ["utf-8", "utf-8-sig", "cp949"])
def test_csv_import_when_supported_encoding_is_used(encoding: str) -> None:
    # Given: the same Korean brokerage export in a supported encoding.
    # When: bytes are parsed in memory with automatic column recognition.
    preview = parse_dividend_file("배당.csv", CSV_TEXT.encode(encoding))

    # Then: one typed dividend row is available for preview.
    assert preview.valid_rows[0].symbol == "005930"
    assert preview.valid_rows[0].payment_date == date(2026, 4, 20)
    assert preview.valid_rows[0].gross_amount == Decimal(10)


def test_xlsx_import_when_workbook_contains_dividend_columns() -> None:
    # Given: an XLSX workbook held entirely in memory.
    workbook = Workbook()
    sheet = workbook.worksheets[0]
    sheet.append(["티커", "종목명", "지급일", "외화 배당금", "제세금", "실수령액", "통화"])
    sheet.append(
        [
            "SCHD",
            "Schwab U.S. Dividend Equity ETF",
            "2026-03-31",
            "12.34",
            "1.85",
            "10.49",
            "USD",
        ]
    )
    content = BytesIO()
    workbook.save(content)

    # When: the XLSX bytes are parsed.
    preview = parse_dividend_file("dividends.xlsx", content.getvalue())

    # Then: numeric and date cells cross the boundary as typed values.
    assert preview.valid_rows[0].symbol == "SCHD"
    assert preview.valid_rows[0].gross_amount == Decimal("12.34")


def test_import_preview_when_row_contains_invalid_values() -> None:
    # Given: a row with an invalid date and amount.
    content = "티커,지급일,배당금,통화\nSCHD,not-a-date,not-money,USD\n".encode()

    # When: the file is parsed for preview.
    preview = parse_dividend_file("bad.csv", content)

    # Then: no row is silently coerced and reasons remain downloadable.
    assert preview.valid_rows == ()
    assert preview.error_rows[0].row_number == 2
    assert {error.field for error in preview.error_rows[0].errors} == {
        "payment_date",
        "gross_amount",
    }


def test_row_hash_when_equivalent_row_is_reuploaded() -> None:
    # Given: equivalent normalized records with distinct display formatting.
    first = {
        "symbol": "SCHD",
        "payment_date": date(2026, 3, 31),
        "gross_amount": Decimal("12.340"),
        "currency": "usd",
    }
    second = {
        "symbol": " schd ",
        "payment_date": date(2026, 3, 31),
        "gross_amount": Decimal("12.34"),
        "currency": "USD",
    }

    # When: deterministic import hashes are generated.
    first_hash = build_import_hash(first)
    second_hash = build_import_hash(second)

    # Then: the same economic event has one idempotency key.
    assert first_hash == second_hash
    assert len(first_hash) == sha256().digest_size * 2
