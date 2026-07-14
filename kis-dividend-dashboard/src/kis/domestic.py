"""공식 국내주식 잔고 조회 응답의 검증과 정규화."""

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.kis.client import KisClient, KisEnvironment
from src.kis.exceptions import KisResponseValidationError
from src.kis.pagination import Cursor, Page, collect_pages

DOMESTIC_BALANCE_PATH: Final = "/uapi/domestic-stock/v1/trading/inquire-balance"


class DomesticBalanceRequest(BaseModel):
    """국내 잔고 조회 입력."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    account_no: str = Field(min_length=8, max_length=8)
    product_code: str = Field(default="01", min_length=2, max_length=2)
    after_hours: str = "N"
    inquiry_division: str = "02"
    unit_price_division: str = "01"
    include_fund_settlement: str = "N"
    auto_repay_financing: str = "N"
    processing_division: str = "00"


class DomesticHoldingApi(BaseModel):
    """공식 국내 잔고 보유종목 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    pdno: str
    prdt_name: str
    hldg_qty: Decimal
    ord_psbl_qty: Decimal
    pchs_avg_pric: Decimal
    pchs_amt: Decimal
    prpr: Decimal
    evlu_amt: Decimal
    evlu_pfls_amt: Decimal
    evlu_pfls_rt: Decimal


class DomesticSummaryApi(BaseModel):
    """공식 국내 잔고 합계 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    dnca_tot_amt: Decimal
    tot_evlu_amt: Decimal
    nass_amt: Decimal


class DomesticBalanceEnvelope(BaseModel):
    """국내 잔고 페이지 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    rt_cd: str
    msg_cd: str
    msg1: str
    ctx_area_fk100: str
    ctx_area_nk100: str
    output1: tuple[DomesticHoldingApi, ...]
    output2: tuple[DomesticSummaryApi, ...]


@dataclass(frozen=True, slots=True)
class DomesticPosition:
    """화면과 저장소에 전달할 국내 보유종목."""

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


@dataclass(frozen=True, slots=True)
class DomesticBalanceResult:
    """모든 연속조회 페이지를 합친 국내 잔고."""

    positions: tuple[DomesticPosition, ...]
    summary: DomesticSummaryApi | None


def fetch_domestic_balance(
    client: KisClient,
    request: DomesticBalanceRequest,
) -> DomesticBalanceResult:
    """공식 연속조회 규칙으로 국내 잔고 전체를 조회합니다."""
    summaries: list[DomesticSummaryApi] = []

    def fetch_page(cursor: Cursor) -> Page[DomesticPosition]:
        response = client.get(
            path=DOMESTIC_BALANCE_PATH,
            tr_id=_balance_tr_id(client.environment),
            tr_cont="" if cursor.fk == "" else "N",
            params={
                "CANO": request.account_no,
                "ACNT_PRDT_CD": request.product_code,
                "AFHR_FLPR_YN": request.after_hours,
                "OFL_YN": "",
                "INQR_DVSN": request.inquiry_division,
                "UNPR_DVSN": request.unit_price_division,
                "FUND_STTL_ICLD_YN": request.include_fund_settlement,
                "FNCG_AMT_AUTO_RDPT_YN": request.auto_repay_financing,
                "PRCS_DVSN": request.processing_division,
                "CTX_AREA_FK100": cursor.fk,
                "CTX_AREA_NK100": cursor.nk,
            },
        )
        try:
            envelope = DomesticBalanceEnvelope.model_validate_json(response.body)
        except ValidationError as error:
            raise KisResponseValidationError(endpoint=DOMESTIC_BALANCE_PATH) from error
        summaries.extend(envelope.output2)
        return Page(
            items=tuple(_position(item) for item in envelope.output1),
            next_cursor=Cursor(envelope.ctx_area_fk100, envelope.ctx_area_nk100),
            has_more=response.tr_cont in {"M", "F"},
        )

    positions = collect_pages(fetch_page)
    return DomesticBalanceResult(positions=positions, summary=summaries[0] if summaries else None)


def _balance_tr_id(environment: KisEnvironment) -> str:
    return "TTTC8434R" if environment is KisEnvironment.REAL else "VTTC8434R"


def _position(item: DomesticHoldingApi) -> DomesticPosition:
    return DomesticPosition(
        symbol=item.pdno,
        name=item.prdt_name,
        quantity=item.hldg_qty,
        available_quantity=item.ord_psbl_qty,
        average_price=item.pchs_avg_pric,
        purchase_amount=item.pchs_amt,
        current_price=item.prpr,
        evaluation_amount=item.evlu_amt,
        profit_loss=item.evlu_pfls_amt,
        profit_rate=item.evlu_pfls_rt,
    )
