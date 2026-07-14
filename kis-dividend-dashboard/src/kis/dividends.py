"""공식 국내 배당일정과 국내·해외 권리내역 조회."""

from dataclasses import dataclass
from decimal import Decimal
from typing import ClassVar, Final

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from src.kis.client import KisClient
from src.kis.exceptions import KisResponseValidationError
from src.kis.pagination import Cursor, Page, collect_pages

DOMESTIC_DIVIDEND_SCHEDULE_PATH: Final = "/uapi/domestic-stock/v1/ksdinfo/dividend"
DOMESTIC_ACCOUNT_RIGHTS_PATH: Final = "/uapi/domestic-stock/v1/trading/period-rights"
OVERSEAS_RIGHTS_PATH: Final = "/uapi/overseas-price/v1/quotations/period-rights"


class DomesticDividendScheduleRequest(BaseModel):
    """국내 배당일정 조회 입력."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    start_date: str = Field(pattern="^[0-9]{8}$")
    end_date: str = Field(pattern="^[0-9]{8}$")
    category: str = "0"
    symbol: str = ""


class DomesticDividendScheduleApi(BaseModel):
    """공식 국내 배당일정 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    record_date: str
    sht_cd: str
    divi_kind: str
    per_sto_divi_amt: Decimal
    divi_pay_dt: str


class DomesticDividendScheduleEnvelope(BaseModel):
    """국내 배당일정 응답 본문."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    rt_cd: str
    msg_cd: str
    msg1: str
    output1: tuple[DomesticDividendScheduleApi, ...]


@dataclass(frozen=True, slots=True)
class DomesticDividendSchedule:
    """정규화한 국내 배당일정."""

    record_date: str
    symbol: str
    dividend_kind: str
    amount_per_share: Decimal
    payment_date: str


class DomesticAccountRightsRequest(BaseModel):
    """국내 계좌 권리내역 조회 입력."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    account_no: str = Field(min_length=8, max_length=8)
    product_code: str = "01"
    start_date: str = Field(pattern="^[0-9]{8}$")
    end_date: str = Field(pattern="^[0-9]{8}$")
    inquiry_division: str = "03"
    rights_type: str = ""
    symbol: str = ""


class DomesticAccountRightApi(BaseModel):
    """공식 국내 계좌 권리내역 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    rght_type_cd: str
    bass_dt: str
    pdno: str
    prdt_name: str
    cblc_qty: Decimal
    cash_dfrm_dt: str = ""
    tax_amt: Decimal = Decimal(0)


class DomesticAccountRightsEnvelope(BaseModel):
    """국내 계좌 권리내역 페이지 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    rt_cd: str
    msg_cd: str
    msg1: str
    ctx_area_fk100: str
    ctx_area_nk100: str
    output: tuple[DomesticAccountRightApi, ...]


class OverseasRightsRequest(BaseModel):
    """해외 권리내역 조회 입력."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True)

    start_date: str = Field(pattern="^[0-9]{8}$")
    end_date: str = Field(pattern="^[0-9]{8}$")
    rights_type: str = "03"
    inquiry_division: str = "02"
    symbol: str = ""
    product_type: str = ""


class OverseasRightApi(BaseModel):
    """공식 해외 권리내역 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    acpl_bass_dt: str
    rght_type_cd: str
    pdno: str
    prdt_name: str
    crcy_cd: str = ""
    stkp_dvdn_frcr_amt2: Decimal = Decimal(0)
    dfnt_yn: str


class OverseasRightsEnvelope(BaseModel):
    """해외 권리내역 페이지 응답."""

    model_config: ClassVar[ConfigDict] = ConfigDict(frozen=True, extra="ignore")

    rt_cd: str
    msg_cd: str
    msg1: str
    ctx_area_fk50: str
    ctx_area_nk50: str
    output: tuple[OverseasRightApi, ...]


def fetch_domestic_dividend_schedule(
    client: KisClient,
    request: DomesticDividendScheduleRequest,
) -> tuple[DomesticDividendSchedule, ...]:
    """공식 KSD 배당일정을 조회합니다."""
    response = client.get(
        path=DOMESTIC_DIVIDEND_SCHEDULE_PATH,
        tr_id="HHKDB669102C0",
        params={
            "CTS": "",
            "GB1": request.category,
            "F_DT": request.start_date,
            "T_DT": request.end_date,
            "SHT_CD": request.symbol,
            "HIGH_GB": "",
        },
    )
    try:
        envelope = DomesticDividendScheduleEnvelope.model_validate_json(response.body)
    except ValidationError as error:
        raise KisResponseValidationError(endpoint=DOMESTIC_DIVIDEND_SCHEDULE_PATH) from error
    return tuple(
        DomesticDividendSchedule(
            record_date=item.record_date,
            symbol=item.sht_cd,
            dividend_kind=item.divi_kind,
            amount_per_share=item.per_sto_divi_amt,
            payment_date=item.divi_pay_dt,
        )
        for item in envelope.output1
    )


def fetch_domestic_account_rights(
    client: KisClient,
    request: DomesticAccountRightsRequest,
) -> tuple[DomesticAccountRightApi, ...]:
    """공식 연속조회 규칙으로 국내 권리내역을 조회합니다."""

    def fetch_page(cursor: Cursor) -> Page[DomesticAccountRightApi]:
        response = client.get(
            path=DOMESTIC_ACCOUNT_RIGHTS_PATH,
            tr_id="CTRGA011R",
            tr_cont="" if cursor.fk == "" else "N",
            params={
                "INQR_DVSN": request.inquiry_division,
                "CANO": request.account_no,
                "ACNT_PRDT_CD": request.product_code,
                "INQR_STRT_DT": request.start_date,
                "INQR_END_DT": request.end_date,
                "CUST_RNCNO25": "",
                "HMID": "",
                "RGHT_TYPE_CD": request.rights_type,
                "PDNO": request.symbol,
                "PRDT_TYPE_CD": "",
                "CTX_AREA_FK100": cursor.fk,
                "CTX_AREA_NK100": cursor.nk,
            },
        )
        try:
            envelope = DomesticAccountRightsEnvelope.model_validate_json(response.body)
        except ValidationError as error:
            raise KisResponseValidationError(endpoint=DOMESTIC_ACCOUNT_RIGHTS_PATH) from error
        return Page(
            items=envelope.output,
            next_cursor=Cursor(envelope.ctx_area_fk100, envelope.ctx_area_nk100),
            has_more=response.tr_cont in {"M", "F"},
        )

    return collect_pages(fetch_page)


def fetch_overseas_rights(
    client: KisClient,
    request: OverseasRightsRequest,
) -> tuple[OverseasRightApi, ...]:
    """공식 연속조회 규칙으로 해외 권리내역을 조회합니다."""

    def fetch_page(cursor: Cursor) -> Page[OverseasRightApi]:
        response = client.get(
            path=OVERSEAS_RIGHTS_PATH,
            tr_id="CTRGT011R",
            tr_cont="" if cursor.fk == "" else "N",
            params={
                "RGHT_TYPE_CD": request.rights_type,
                "INQR_DVSN_CD": request.inquiry_division,
                "INQR_STRT_DT": request.start_date,
                "INQR_END_DT": request.end_date,
                "PDNO": request.symbol,
                "PRDT_TYPE_CD": request.product_type,
                "CTX_AREA_FK50": cursor.fk,
                "CTX_AREA_NK50": cursor.nk,
            },
        )
        try:
            envelope = OverseasRightsEnvelope.model_validate_json(response.body)
        except ValidationError as error:
            raise KisResponseValidationError(endpoint=OVERSEAS_RIGHTS_PATH) from error
        return Page(
            items=envelope.output,
            next_cursor=Cursor(envelope.ctx_area_fk50, envelope.ctx_area_nk50),
            has_more=response.tr_cont in {"M", "F"},
        )

    return collect_pages(fetch_page)
