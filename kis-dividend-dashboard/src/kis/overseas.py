"""공식 해외주식 잔고 조회 응답의 검증과 정규화."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum, unique
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.kis.client import KisClient, KisEnvironment
from src.kis.exceptions import KisResponseValidationError
from src.kis.pagination import Cursor, Page, collect_pages

OVERSEAS_BALANCE_PATH: Final = "/uapi/overseas-stock/v1/trading/inquire-balance"


@unique
class OverseasExchange(StrEnum):
    """공식 해외잔고 조회에서 사용하는 거래소 코드."""

    NASD = "NASD"
    NAS = "NAS"
    NYSE = "NYSE"
    AMEX = "AMEX"
    SEHK = "SEHK"
    SHAA = "SHAA"
    SZAA = "SZAA"
    TKSE = "TKSE"
    HASE = "HASE"
    VNSE = "VNSE"


class OverseasBalanceRequest(BaseModel):
    """해외 잔고 조회 입력."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    account_no: str = Field(min_length=8, max_length=8)
    product_code: str = Field(default="01", min_length=2, max_length=2)
    exchange: OverseasExchange
    currency: str = Field(pattern="^(USD|HKD|CNY|JPY|VND)$")


class OverseasHoldingApi(BaseModel):
    """공식 해외 잔고 보유종목 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    ovrs_pdno: str
    ovrs_item_name: str = ""
    ovrs_cblc_qty: Decimal
    ord_psbl_qty: Decimal
    pchs_avg_pric: Decimal
    frcr_pchs_amt1: Decimal
    now_pric2: Decimal
    ovrs_stck_evlu_amt: Decimal
    frcr_evlu_pfls_amt: Decimal
    evlu_pfls_rt: Decimal
    tr_crcy_cd: str
    ovrs_excg_cd: str


class OverseasBalanceEnvelope(BaseModel):
    """해외 잔고 페이지 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    rt_cd: str
    msg_cd: str
    msg1: str
    ctx_area_fk200: str
    ctx_area_nk200: str
    output1: tuple[OverseasHoldingApi, ...]


@dataclass(frozen=True, slots=True)
class OverseasPosition:
    """화면과 저장소에 전달할 해외 보유종목."""

    exchange: str
    symbol: str
    name: str
    quantity: Decimal
    available_quantity: Decimal
    average_price: Decimal
    purchase_amount: Decimal
    current_price: Decimal
    evaluation_amount: Decimal
    profit_loss: Decimal
    profit_rate: Decimal
    currency: str


@dataclass(frozen=True, slots=True)
class OverseasBalanceResult:
    """모든 연속조회 페이지를 합친 해외 잔고."""

    positions: tuple[OverseasPosition, ...]


def fetch_overseas_balance(
    client: KisClient,
    request: OverseasBalanceRequest,
) -> OverseasBalanceResult:
    """공식 연속조회 규칙으로 한 거래소의 해외 잔고를 조회합니다."""

    def fetch_page(cursor: Cursor) -> Page[OverseasPosition]:
        response = client.get(
            path=OVERSEAS_BALANCE_PATH,
            tr_id=_balance_tr_id(client.environment),
            tr_cont="" if cursor.fk == "" else "N",
            params={
                "CANO": request.account_no,
                "ACNT_PRDT_CD": request.product_code,
                "OVRS_EXCG_CD": request.exchange.value,
                "TR_CRCY_CD": request.currency,
                "CTX_AREA_FK200": cursor.fk,
                "CTX_AREA_NK200": cursor.nk,
            },
        )
        try:
            envelope = OverseasBalanceEnvelope.model_validate_json(response.body)
        except ValidationError as error:
            raise KisResponseValidationError(endpoint=OVERSEAS_BALANCE_PATH) from error
        return Page(
            items=tuple(_position(item) for item in envelope.output1),
            next_cursor=Cursor(envelope.ctx_area_fk200, envelope.ctx_area_nk200),
            has_more=response.tr_cont in {"M", "F"},
        )

    return OverseasBalanceResult(positions=collect_pages(fetch_page))


def _balance_tr_id(environment: KisEnvironment) -> str:
    return "TTTS3012R" if environment is KisEnvironment.REAL else "VTTS3012R"


def _position(item: OverseasHoldingApi) -> OverseasPosition:
    return OverseasPosition(
        exchange=item.ovrs_excg_cd,
        symbol=item.ovrs_pdno,
        name=item.ovrs_item_name,
        quantity=item.ovrs_cblc_qty,
        available_quantity=item.ord_psbl_qty,
        average_price=item.pchs_avg_pric,
        purchase_amount=item.frcr_pchs_amt1,
        current_price=item.now_pric2,
        evaluation_amount=item.ovrs_stck_evlu_amt,
        profit_loss=item.frcr_evlu_pfls_amt,
        profit_rate=item.evlu_pfls_rt,
        currency=item.tr_crcy_cd,
    )
