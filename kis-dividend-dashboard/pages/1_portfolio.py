"""Domestic and overseas portfolio page."""

# ruff: noqa: N999

import pandas as pd
import streamlit as st
from src.ui.auth import require_authentication
from src.ui.components import empty_state, render_source
from src.ui.data_access import portfolio_view
from src.ui.shell import render_page_header, render_sync_action

if not require_authentication():
    st.stop()

is_demo = render_page_header("잔고", "국내·해외 보유 종목과 원화 환산 평가금액을 조회합니다.")
render_sync_action(is_demo=is_demo)
data = portfolio_view(is_demo=is_demo)
render_source(data.source)
positions = data.positions.copy()

if positions.empty:
    empty_state("조회된 보유 종목이 없습니다.", "지금 동기화를 실행한 뒤 다시 확인해 주세요.")
    st.stop()

with st.expander("필터", expanded=False):
    market = st.selectbox("시장", ["전체", *sorted(positions["시장"].dropna().unique().tolist())])
    exchange = st.selectbox(
        "거래소", ["전체", *sorted(positions["거래소"].dropna().unique().tolist())]
    )
    currency = st.selectbox("통화", ["전체", *sorted(positions["통화"].dropna().unique().tolist())])
    query = st.text_input("종목 검색", placeholder="종목명 또는 종목코드")

filtered = positions
if market != "전체":
    filtered = filtered.loc[filtered["시장"] == market]
if exchange != "전체":
    filtered = filtered.loc[filtered["거래소"] == exchange]
if currency != "전체":
    filtered = filtered.loc[filtered["통화"] == currency]
if query:
    normalized = query.strip().casefold()
    filtered = filtered.loc[
        filtered["종목명"].str.casefold().str.contains(normalized, regex=False)
        | filtered["종목코드"].str.casefold().str.contains(normalized, regex=False)
    ]

if filtered.empty:
    empty_state("필터와 일치하는 종목이 없습니다.", "필터를 변경하거나 검색어를 지워 주세요.")
    st.stop()

st.subheader(f"보유 종목 {len(filtered):,}개")
compact_columns = [
    "종목명",
    "수량",
    "원화 평가금액",
    "수익률",
]
st.dataframe(
    filtered.loc[:, compact_columns],
    width="stretch",
    hide_index=True,
    column_config={
        "수량": st.column_config.NumberColumn("수량", format="%.4f"),
        "원화 평가금액": st.column_config.NumberColumn("원화 평가금액", format="%.0f원"),
        "원화 평가손익": st.column_config.NumberColumn("원화 평가손익", format="%+.0f원"),
        "수익률": st.column_config.NumberColumn("수익률", format="%+.2f%%"),
    },
)

with st.expander("전체 잔고 열 보기"):
    st.dataframe(filtered, width="stretch", hide_index=True)

selected_name = st.selectbox("종목 상세 보기", filtered["종목명"].tolist())
selected = filtered.loc[filtered["종목명"] == selected_name].iloc[0]
detail = pd.DataFrame(
    {
        "항목": ["시장", "거래소", "종목코드", "통화", "수량", "평가금액", "평가손익", "수익률"],
        "값": [
            selected["시장"],
            selected["거래소"],
            selected["종목코드"],
            selected["통화"],
            str(selected["수량"]),
            str(selected["원화 평가금액"]),
            str(selected["원화 평가손익"]),
            str(selected["수익률"]),
        ],
    }
)
st.dataframe(detail, width="stretch", hide_index=True)
