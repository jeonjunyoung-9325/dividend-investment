"""Validate and normalize the official MiniStock balance response."""

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.kis.client import KisClient, KisEnvironment
from src.kis.exceptions import KisPaginationError, KisResponseValidationError

MINISTOCK_BALANCE_PATH: Final = "/uapi/overseas-stock/v1/trading/inquire-present-balance"
MAX_PAGES: Final = 10


class MiniStockBalanceRequest(BaseModel):
    """Validated MiniStock balance query parameters."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    account_no: str = Field(min_length=8, max_length=8)
    product_code: str = Field(default="01", min_length=2, max_length=2)


class MiniStockHoldingApi(BaseModel):
    """Required fields from one official holding row."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    pdno: str
    prdt_name: str
    cblc_qty13: Decimal
    ord_psbl_qty1: Decimal
    avg_unpr3: Decimal
    ovrs_now_pric1: Decimal
    frcr_pchs_amt: Decimal
    frcr_evlu_amt2: Decimal
    evlu_pfls_amt2: Decimal
    evlu_pfls_rt1: Decimal
    bass_exrt: Decimal
    buy_crcy_cd: str
    ovrs_excg_cd: str


class MiniStockBalanceEnvelope(BaseModel):
    """Validated page envelope returned by KIS."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    rt_cd: str
    msg_cd: str
    msg1: str
    output1: tuple[MiniStockHoldingApi, ...]


@dataclass(frozen=True, slots=True)
class MiniStockPosition:
    """Normalized MiniStock holding passed to portfolio services."""

    exchange: str
    symbol: str
    name: str
    quantity: Decimal
    available_quantity: Decimal
    average_price: Decimal
    current_price: Decimal
    purchase_amount: Decimal
    evaluation_amount: Decimal
    profit_loss: Decimal
    profit_rate: Decimal
    currency: str
    exchange_rate: Decimal


@dataclass(frozen=True, slots=True)
class MiniStockBalanceResult:
    """Deduplicated holdings from all continuation pages."""

    positions: tuple[MiniStockPosition, ...]


def fetch_ministock_balance(
    client: KisClient,
    request: MiniStockBalanceRequest,
) -> MiniStockBalanceResult:
    """Fetch every MiniStock-only balance page."""
    positions: dict[tuple[str, str], MiniStockPosition] = {}
    tr_cont = ""
    for _page_number in range(1, MAX_PAGES + 1):
        response = client.get(
            path=MINISTOCK_BALANCE_PATH,
            tr_id=_balance_tr_id(client.environment),
            tr_cont=tr_cont,
            params={
                "CANO": request.account_no,
                "ACNT_PRDT_CD": request.product_code,
                "WCRC_FRCR_DVSN_CD": "02",
                "NATN_CD": "000",
                "TR_MKET_CD": "00",
                "INQR_DVSN_CD": "02",
            },
        )
        try:
            envelope = MiniStockBalanceEnvelope.model_validate_json(response.body)
        except ValidationError as error:
            raise KisResponseValidationError(endpoint=MINISTOCK_BALANCE_PATH) from error
        for item in envelope.output1:
            position = _position(item)
            positions[(position.exchange, position.symbol)] = position
        if response.tr_cont not in {"M", "F"}:
            return MiniStockBalanceResult(tuple(positions.values()))
        tr_cont = "N"
    raise KisPaginationError(pages_requested=MAX_PAGES)


def _balance_tr_id(environment: KisEnvironment) -> str:
    return "CTRP6504R" if environment is KisEnvironment.REAL else "VTRP6504R"


def _position(item: MiniStockHoldingApi) -> MiniStockPosition:
    return MiniStockPosition(
        exchange=item.ovrs_excg_cd,
        symbol=item.pdno,
        name=item.prdt_name,
        quantity=item.cblc_qty13,
        available_quantity=item.ord_psbl_qty1,
        average_price=item.avg_unpr3,
        current_price=item.ovrs_now_pric1,
        purchase_amount=item.frcr_pchs_amt,
        evaluation_amount=item.frcr_evlu_amt2,
        profit_loss=item.evlu_pfls_amt2,
        profit_rate=item.evlu_pfls_rt1,
        currency=item.buy_crcy_cd,
        exchange_rate=item.bass_exrt,
    )
