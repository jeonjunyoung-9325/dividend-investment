"""Actual, confirmed, forecast, and imported dividends page."""

# ruff: noqa: N999

import csv
from datetime import datetime
from decimal import Decimal
from io import StringIO

import pandas as pd
import streamlit as st
from src.ui.auth import require_authentication
from src.ui.components import empty_state, render_source
from src.ui.data_access import (
    commit_dividend_import,
    dividend_view,
    preview_dividend_import,
)
from src.ui.formatting import KST, money
from src.ui.shell import render_page_header, render_sync_action
from src.ui.viewmodels import ImportColumnMapping

ROLLING_YEAR_DAYS = 365


def _sum_decimal(frame: pd.DataFrame, column: str) -> Decimal:
    if frame.empty or column not in frame:
        return Decimal(0)
    return sum((value for value in frame[column] if value is not None), Decimal(0))


if not require_authentication():
    st.stop()

is_demo = render_page_header(
    "배당", "실제 입금, 확정 예정, 예상 배당을 서로 다른 근거로 표시합니다."
)
render_sync_action(is_demo=is_demo)
data = dividend_view(is_demo=is_demo)
render_source(data.source)
st.info(
    "실제는 계좌 입금 내역입니다. 확정은 발표·수령 자격 확인값입니다. "
    "예상은 과거 이력 기반 추정치입니다."
)

actual_tab, confirmed_tab, forecast_tab, history_tab, import_tab = st.tabs(
    ["실제 받은 배당금", "확정 예정 배당금", "예상 배당금", "종목별 배당 이력", "파일 가져오기"]
)

with actual_tab:
    if data.actual.empty:
        empty_state(
            "등록된 실제 배당 내역이 없습니다.",
            "한국투자 CSV·XLSX 파일을 가져오거나 직접 입력해 주세요.",
        )
    else:
        today = datetime.now(KST).date()
        year_rows = data.actual[data.actual["지급일"].map(lambda value: value.year == today.year)]
        rolling_rows = data.actual[
            data.actual["지급일"].map(lambda value: (today - value).days <= ROLLING_YEAR_DAYS)
        ]
        first, second, third, fourth = st.columns(4)
        first.metric("올해 세전", money(_sum_decimal(year_rows, "원화 세전")))
        second.metric("올해 세금", money(_sum_decimal(year_rows, "원화 세금")))
        third.metric("올해 실수령", money(_sum_decimal(year_rows, "원화 실수령")))
        fourth.metric("최근 12개월 실수령", money(_sum_decimal(rolling_rows, "원화 실수령")))
        essential_columns = ["종목", "지급일", "실수령", "통화", "구분"]
        essential = [column for column in essential_columns if column in data.actual]
        st.dataframe(data.actual.loc[:, essential], width="stretch", hide_index=True)
        with st.expander("실제 배당 전체 열 보기"):
            st.dataframe(data.actual, width="stretch", hide_index=True)

with confirmed_tab:
    st.caption("배당 기준일 당시 보유 수량을 확인할 수 없는 경우 수령 자격 확인 필요로 표시합니다.")
    if data.confirmed.empty:
        empty_state(
            "확정된 예정 배당이 없습니다.",
            "발표된 배당 이벤트와 기준일 보유 수량이 확인되면 표시됩니다.",
        )
    else:
        st.dataframe(data.confirmed, width="stretch", hide_index=True)

with forecast_tab:
    st.warning("추정치이며 실제 지급액과 다를 수 있습니다.")
    st.caption("실제 세금은 국가·상품·계좌 유형·개인 상황에 따라 달라집니다.")
    if data.forecast.empty:
        empty_state(
            "예상 배당을 계산할 수 없습니다.",
            "배당 이력과 현재 보유 수량이 충분한지 확인해 주세요.",
        )
    else:
        available = data.forecast[data.forecast["예상 세전 원화"].notna()]
        first, second, third = st.columns(3)
        first.metric("향후 12개월 예상 세전", money(_sum_decimal(available, "예상 세전 원화")))
        second.metric(
            "예상 원천징수",
            money(
                _sum_decimal(available, "예상 세전 원화")
                - _sum_decimal(available, "예상 세후 원화")
            ),
        )
        third.metric("향후 12개월 예상 세후", money(_sum_decimal(available, "예상 세후 원화")))
        unavailable_count = len(data.forecast) - len(available)
        if unavailable_count:
            st.caption(f"계산 불가: {unavailable_count}개 종목 (배당 이력 부족 또는 환율 없음)")
        st.caption("종목별 금액 표는 좌우로 밀어 볼 수 있습니다.")
        forecast_columns = ["종목", "예상 세전 원화", "예상 세후 원화"]
        compact_columns = [column for column in forecast_columns if column in data.forecast]
        st.dataframe(data.forecast.loc[:, compact_columns], width="stretch", hide_index=True)
        with st.expander("예상 배당 근거 전체 열 보기"):
            st.dataframe(data.forecast, width="stretch", hide_index=True)

with history_tab:
    if data.history.empty:
        empty_state(
            "배당 이력이 없습니다.", "실제 배당 파일을 가져오거나 배당 이벤트를 동기화해 주세요."
        )
    else:
        st.dataframe(data.history, width="stretch", hide_index=True)

with import_tab:
    template = (
        "종목코드,종목명,지급일,세전 배당금,세금,실수령액,통화,거래소,수량,주당배당금,환율\n"
        "SCHD,Schwab US Dividend Equity ETF,2026-06-30,25.00,3.75,21.25,USD,NASD,10,2.50,1380\n"
    )
    st.download_button(
        "배당 내역 CSV 양식 다운로드",
        template.encode("utf-8-sig"),
        file_name="dividend_import_template.csv",
        mime="text/csv",
    )
    uploaded = st.file_uploader("한국투자 거래·배당 내역", type=["csv", "xlsx"])
    if uploaded is not None:
        content = uploaded.getvalue()
        preview = preview_dividend_import(uploaded.name, content)
        st.caption(
            f"감지 인코딩: {preview.detected_encoding} · 파일 식별값: {preview.file_hash[:12]}…"
        )
        st.subheader("컬럼 매핑")
        targets = [
            "사용 안 함",
            "symbol",
            "name",
            "payment_date",
            "gross_amount",
            "tax_amount",
            "net_amount",
            "currency",
            "exchange",
            "quantity",
            "amount_per_share",
            "krw_exchange_rate",
        ]
        detected_targets = {item.source: item.target for item in preview.detected_mappings}
        mappings = tuple(
            ImportColumnMapping(
                source=column,
                target=st.selectbox(
                    column,
                    targets,
                    index=targets.index(detected_targets.get(column, "사용 안 함")),
                    key=f"map-{column}",
                ),
            )
            for column in preview.preview.columns
        )
        st.subheader("저장 전 미리보기")
        st.dataframe(preview.preview, width="stretch", hide_index=True)
        left, middle, right = st.columns(3)
        left.metric("유효 후보", len(preview.preview))
        middle.metric("중복 후보", len(preview.duplicates))
        right.metric("오류 행", len(preview.errors))
        if not preview.duplicates.empty:
            with st.expander("중복 후보 보기"):
                st.dataframe(preview.duplicates, width="stretch", hide_index=True)
        confirmed = st.checkbox("미리보기와 중복 후보를 확인했으며 유효한 행을 저장합니다.")
        if st.button("배당 내역 저장", type="primary", disabled=not confirmed):
            result = commit_dividend_import(uploaded.name, content, mappings)
            st.success(f"저장 {result.saved}건 · 제외 {result.excluded}건 · 오류 {result.errors}건")
            if result.error_rows_csv:
                st.download_button(
                    "오류 행 CSV 다운로드",
                    result.error_rows_csv,
                    file_name="dividend_import_errors.csv",
                    mime="text/csv",
                )

    st.divider()
    with st.expander("실제 배당 직접 입력"):
        with st.form("manual-dividend"):
            manual_symbol = st.text_input("종목코드 또는 티커")
            manual_name = st.text_input("종목명")
            manual_payment_date = st.date_input("지급일")
            manual_gross = st.text_input("세전 배당금", placeholder="1234.56")
            manual_tax = st.text_input("세금", placeholder="0")
            manual_net = st.text_input("실수령액", placeholder="1234.56")
            manual_currency = st.selectbox("통화", ["KRW", "USD", "JPY", "HKD", "CNY"])
            manual_exchange = st.text_input("거래소", placeholder="KRX 또는 NASD")
            manual_quantity = st.text_input("기준일 수량 (선택)")
            manual_per_share = st.text_input("주당 배당금 (선택)")
            manual_rate = st.text_input("원화 환율 (해외 배당 선택)")
            manual_submit = st.form_submit_button("직접 입력 저장", type="primary")
        if manual_submit:
            output = StringIO()
            writer = csv.writer(output)
            columns = (
                "symbol",
                "name",
                "payment_date",
                "gross_amount",
                "tax_amount",
                "net_amount",
                "currency",
                "exchange",
                "quantity",
                "amount_per_share",
                "krw_exchange_rate",
            )
            writer.writerow(columns)
            writer.writerow(
                (
                    manual_symbol,
                    manual_name,
                    manual_payment_date.isoformat(),
                    manual_gross,
                    manual_tax,
                    manual_net,
                    manual_currency,
                    manual_exchange,
                    manual_quantity,
                    manual_per_share,
                    manual_rate,
                )
            )
            manual_result = commit_dividend_import(
                "manual-dividend.csv",
                output.getvalue().encode("utf-8-sig"),
                tuple(ImportColumnMapping(source=column, target=column) for column in columns),
                source="manual",
            )
            if manual_result.saved:
                st.success("실제 배당 내역 1건을 저장했습니다.")
            else:
                st.error("입력값을 저장하지 못했습니다. 필수값과 숫자 형식을 확인해 주세요.")
                if manual_result.error_rows_csv:
                    st.download_button(
                        "직접 입력 오류 CSV 다운로드",
                        manual_result.error_rows_csv,
                        file_name="manual_dividend_error.csv",
                        mime="text/csv",
                    )
