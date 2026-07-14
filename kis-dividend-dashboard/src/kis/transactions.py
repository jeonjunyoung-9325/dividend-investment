"""공식 국내·해외 거래내역 조회와 응답 검증."""

from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum, unique
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.kis.client import KisClient, KisEnvironment
from src.kis.exceptions import KisResponseValidationError
from src.kis.pagination import Cursor, Page, collect_pages

DOMESTIC_TRANSACTIONS_PATH: Final = "/uapi/domestic-stock/v1/trading/inquire-daily-ccld"
OVERSEAS_TRANSACTIONS_PATH: Final = "/uapi/overseas-stock/v1/trading/inquire-period-trans"


@unique
class TransactionPeriod(StrEnum):
    """공식 국내 체결조회 TR 구간."""

    INNER = "inner"
    BEFORE = "before"


class DomesticTransactionsRequest(BaseModel):
    """국내 거래내역 조회 입력."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    account_no: str = Field(min_length=8, max_length=8)
    product_code: str = Field(default="01", min_length=2, max_length=2)
    start_date: str = Field(pattern="^[0-9]{8}$")
    end_date: str = Field(pattern="^[0-9]{8}$")
    period: TransactionPeriod = TransactionPeriod.INNER
    sell_buy_code: str = "00"
    execution_code: str = "01"
    inquiry_order: str = "00"
    inquiry_type: str = "00"
    symbol: str = ""
    exchange_id: str = "ALL"


class DomesticTransactionApi(BaseModel):
    """공식 국내 체결내역 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    ord_dt: str
    pdno: str
    prdt_name: str
    sll_buy_dvsn_cd: str
    tot_ccld_qty: Decimal
    avg_prvs: Decimal
    tot_ccld_amt: Decimal


class DomesticTransactionsEnvelope(BaseModel):
    """국내 체결내역 페이지 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    rt_cd: str
    msg_cd: str
    msg1: str
    ctx_area_fk100: str
    ctx_area_nk100: str
    output1: tuple[DomesticTransactionApi, ...]


class OverseasTransactionsRequest(BaseModel):
    """해외 거래내역 조회 입력."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    account_no: str = Field(min_length=8, max_length=8)
    product_code: str = Field(default="01", min_length=2, max_length=2)
    start_date: str = Field(pattern="^[0-9]{8}$")
    end_date: str = Field(pattern="^[0-9]{8}$")
    exchange: str
    symbol: str = ""
    sell_buy_code: str = "00"
    loan_code: str = ""


class OverseasTransactionApi(BaseModel):
    """공식 해외 거래내역 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    trad_dt: str
    sttl_dt: str
    pdno: str
    ovrs_item_name: str
    sll_buy_dvsn_cd: str
    ccld_qty: Decimal
    ovrs_stck_ccld_unpr: Decimal
    tr_frcr_amt2: Decimal
    wcrc_excc_amt: Decimal
    crcy_cd: str
    erlm_exrt: Decimal


class OverseasTransactionsEnvelope(BaseModel):
    """해외 거래내역 페이지 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    rt_cd: str
    msg_cd: str
    msg1: str
    ctx_area_fk100: str
    ctx_area_nk100: str
    output2: tuple[OverseasTransactionApi, ...]


@dataclass(frozen=True, slots=True)
class OverseasTransaction:
    """정규화한 해외 거래내역."""

    trade_date: str
    settlement_date: str
    symbol: str
    name: str
    sell_buy_code: str
    quantity: Decimal
    execution_price: Decimal
    foreign_amount: Decimal
    krw_amount: Decimal
    currency: str
    exchange_rate: Decimal


def fetch_domestic_transactions(
    client: KisClient,
    request: DomesticTransactionsRequest,
) -> tuple[DomesticTransactionApi, ...]:
    """공식 연속조회 규칙으로 국내 거래내역을 조회합니다."""

    def fetch_page(cursor: Cursor) -> Page[DomesticTransactionApi]:
        response = client.get(
            path=DOMESTIC_TRANSACTIONS_PATH,
            tr_id=_domestic_transaction_tr_id(client.environment, request.period),
            tr_cont="" if cursor.fk == "" else "N",
            params={
                "CANO": request.account_no,
                "ACNT_PRDT_CD": request.product_code,
                "INQR_STRT_DT": request.start_date,
                "INQR_END_DT": request.end_date,
                "SLL_BUY_DVSN_CD": request.sell_buy_code,
                "PDNO": request.symbol,
                "CCLD_DVSN": request.execution_code,
                "INQR_DVSN": request.inquiry_order,
                "INQR_DVSN_3": request.inquiry_type,
                "ORD_GNO_BRNO": "",
                "ODNO": "",
                "INQR_DVSN_1": "",
                "CTX_AREA_FK100": cursor.fk,
                "CTX_AREA_NK100": cursor.nk,
                "EXCG_ID_DVSN_CD": request.exchange_id,
            },
        )
        try:
            envelope = DomesticTransactionsEnvelope.model_validate_json(response.body)
        except ValidationError as error:
            raise KisResponseValidationError(endpoint=DOMESTIC_TRANSACTIONS_PATH) from error
        return Page(
            items=envelope.output1,
            next_cursor=Cursor(envelope.ctx_area_fk100, envelope.ctx_area_nk100),
            has_more=response.tr_cont in {"M", "F"},
        )

    return collect_pages(fetch_page)


def fetch_overseas_transactions(
    client: KisClient,
    request: OverseasTransactionsRequest,
) -> tuple[OverseasTransaction, ...]:
    """공식 연속조회 규칙으로 해외 거래내역을 조회합니다."""

    def fetch_page(cursor: Cursor) -> Page[OverseasTransaction]:
        response = client.get(
            path=OVERSEAS_TRANSACTIONS_PATH,
            tr_id="CTOS4001R",
            tr_cont="" if cursor.fk == "" else "N",
            params={
                "CANO": request.account_no,
                "ACNT_PRDT_CD": request.product_code,
                "ERLM_STRT_DT": request.start_date,
                "ERLM_END_DT": request.end_date,
                "OVRS_EXCG_CD": request.exchange,
                "PDNO": request.symbol,
                "SLL_BUY_DVSN_CD": request.sell_buy_code,
                "LOAN_DVSN_CD": request.loan_code,
                "CTX_AREA_FK100": cursor.fk,
                "CTX_AREA_NK100": cursor.nk,
            },
        )
        try:
            envelope = OverseasTransactionsEnvelope.model_validate_json(response.body)
        except ValidationError as error:
            raise KisResponseValidationError(endpoint=OVERSEAS_TRANSACTIONS_PATH) from error
        return Page(
            items=tuple(_overseas_transaction(item) for item in envelope.output2),
            next_cursor=Cursor(envelope.ctx_area_fk100, envelope.ctx_area_nk100),
            has_more=response.tr_cont in {"M", "F"},
        )

    return collect_pages(fetch_page)


def _domestic_transaction_tr_id(environment: KisEnvironment, period: TransactionPeriod) -> str:
    return {
        (KisEnvironment.REAL, TransactionPeriod.INNER): "TTTC0081R",
        (KisEnvironment.REAL, TransactionPeriod.BEFORE): "CTSC9215R",
        (KisEnvironment.DEMO, TransactionPeriod.INNER): "VTTC0081R",
        (KisEnvironment.DEMO, TransactionPeriod.BEFORE): "VTSC9215R",
    }[(environment, period)]


def _overseas_transaction(item: OverseasTransactionApi) -> OverseasTransaction:
    return OverseasTransaction(
        trade_date=item.trad_dt,
        settlement_date=item.sttl_dt,
        symbol=item.pdno,
        name=item.ovrs_item_name,
        sell_buy_code=item.sll_buy_dvsn_cd,
        quantity=item.ccld_qty,
        execution_price=item.ovrs_stck_ccld_unpr,
        foreign_amount=item.tr_frcr_amt2,
        krw_amount=item.wcrc_excc_amt,
        currency=item.crcy_cd,
        exchange_rate=item.erlm_exrt,
    )
