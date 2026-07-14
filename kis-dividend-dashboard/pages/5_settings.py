"""Browser-safe display and forecast settings page."""

# ruff: noqa: N999

from decimal import Decimal

import pandas as pd
import streamlit as st
from src.ui.auth import require_authentication
from src.ui.data_access import editable_settings, save_editable_settings
from src.ui.shell import render_page_header
from src.ui.viewmodels import EditableSettingView, SymbolForecastOverride

EXCHANGES = ("NASD", "NAS", "NYSE", "AMEX", "SEHK", "SHAA", "SZAA", "TKSE", "HASE", "VNSE")
FORECAST_METHODS = (
    "last_12_months",
    "six_month_median",
    "three_month_average",
    "last_four",
    "last_two",
    "last_one",
    "manual",
)

if not require_authentication():
    st.stop()

is_demo = render_page_header("설정", "표시, 예상 세율, 배당 예측 및 해외 거래소 설정을 관리합니다.")
settings = editable_settings(is_demo=is_demo)

with st.form("editable-settings"):
    st.subheader("표시")
    display_currency = st.selectbox(
        "기본 표시 통화",
        ["KRW", "USD", "JPY"],
        index=["KRW", "USD", "JPY"].index(settings.display_currency),
    )
    decimal_places = st.number_input(
        "표시 자릿수", min_value=0, max_value=6, value=settings.decimal_places
    )

    st.subheader("예상 세율")
    domestic = st.number_input(
        "국내 배당 가정 세율 (%)", 0.0, 100.0, float(settings.domestic_tax_rate * 100)
    )
    us = st.number_input("미국 배당 가정 세율 (%)", 0.0, 100.0, float(settings.us_tax_rate * 100))
    overseas = st.number_input(
        "기타 해외 배당 가정 세율 (%)", 0.0, 100.0, float(settings.overseas_tax_rate * 100)
    )
    st.caption("세후 금액은 단순 추정이며 최종 세무 판단을 제공하지 않습니다.")

    st.subheader("해외 거래소")
    enabled = st.multiselect(
        "조회할 거래소",
        EXCHANGES,
        default=settings.enabled_exchanges,
    )

    st.subheader("종목별 배당 가정")
    st.caption("세율은 0~1 소수로 입력합니다. 직접 입력 방식은 연간 주당 배당금을 함께 입력하세요.")
    override_rows = pd.DataFrame(
        [
            {
                "종목코드": row.symbol,
                "가정 세율": float(row.tax_rate) if row.tax_rate is not None else None,
                "예측 방식": row.forecast_method,
                "연간 주당 배당금": (
                    float(row.manual_annual_per_share)
                    if row.manual_annual_per_share is not None
                    else None
                ),
            }
            for row in settings.symbol_overrides
        ],
        columns=["종목코드", "가정 세율", "예측 방식", "연간 주당 배당금"],
    )
    edited_overrides = st.data_editor(
        override_rows,
        num_rows="dynamic",
        hide_index=True,
        column_config={
            "예측 방식": st.column_config.SelectboxColumn(options=FORECAST_METHODS),
            "가정 세율": st.column_config.NumberColumn(min_value=0.0, max_value=1.0),
            "연간 주당 배당금": st.column_config.NumberColumn(min_value=0.0),
        },
    )
    submitted = st.form_submit_button("설정 저장", type="primary")

if submitted:
    symbol_overrides = tuple(
        SymbolForecastOverride(
            symbol=str(row["종목코드"]).strip().upper(),
            tax_rate=(Decimal(str(row["가정 세율"])) if pd.notna(row["가정 세율"]) else None),
            forecast_method=(str(row["예측 방식"]) if pd.notna(row["예측 방식"]) else None),
            manual_annual_per_share=(
                Decimal(str(row["연간 주당 배당금"])) if pd.notna(row["연간 주당 배당금"]) else None
            ),
        )
        for _, row in edited_overrides.iterrows()
        if str(row["종목코드"]).strip()
    )
    updated = EditableSettingView(
        display_currency=display_currency,
        domestic_tax_rate=Decimal(str(domestic)) / Decimal(100),
        us_tax_rate=Decimal(str(us)) / Decimal(100),
        overseas_tax_rate=Decimal(str(overseas)) / Decimal(100),
        enabled_exchanges=tuple(enabled),
        decimal_places=int(decimal_places),
        symbol_overrides=symbol_overrides,
    )
    save_editable_settings(updated, is_demo=is_demo)
    st.success("설정을 저장했습니다.")

st.divider()
st.subheader("Secret에서만 관리되는 값")
st.caption(
    "App Key, App Secret, 계좌번호, DB 접속정보, 로그인 비밀번호 hash, 토큰 암호화 키, 세션 Secret"
)
st.info("보안을 위해 위 값은 화면에 표시하거나 수정할 수 없습니다.")
