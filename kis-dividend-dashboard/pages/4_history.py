"""Daily account snapshot history page."""

# ruff: noqa: N999

from datetime import timedelta

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from src.ui.auth import require_authentication
from src.ui.components import empty_state, render_chart, render_source
from src.ui.data_access import history_view
from src.ui.shell import render_page_header, render_sync_action

if not require_authentication():
    st.stop()

is_demo = render_page_header("자산 이력", "일별 잔고 스냅샷과 국내·해외 자산 변화를 확인합니다.")
render_sync_action(is_demo=is_demo)
data = history_view(is_demo=is_demo)
render_source(data.source)
snapshots = data.snapshots.rename(
    columns={
        "date": "날짜",
        "total_value_krw": "총 평가자산",
        "domestic_value_krw": "국내",
        "overseas_value_krw": "해외",
    }
).copy()

if snapshots.empty:
    empty_state("저장된 잔고 스냅샷이 없습니다.", "동기화가 완료되면 일별 자산 이력이 쌓입니다.")
    st.stop()

period = st.segmented_control("기간", ["1개월", "3개월", "6개월", "1년", "전체"], default="1개월")
days = {"1개월": 31, "3개월": 92, "6개월": 183, "1년": 366, "전체": None}[period]
snapshots["날짜"] = pd.to_datetime(snapshots["날짜"])
filtered = (
    snapshots
    if days is None
    else snapshots.loc[snapshots["날짜"] >= snapshots["날짜"].max() - timedelta(days=days)]
)

asset_figure = go.Figure()
asset_figure.add_scatter(
    x=filtered["날짜"], y=filtered["총 평가자산"], mode="lines", name="총 평가자산"
)
asset_figure.update_layout(title="총 평가자산", yaxis_title="원")
render_chart(
    asset_figure, "선택 기간의 일별 원화 환산 평가자산입니다.", filtered, key="history-total"
)

market_figure = go.Figure()
market_figure.add_scatter(x=filtered["날짜"], y=filtered["국내"], mode="lines", name="국내")
market_figure.add_scatter(x=filtered["날짜"], y=filtered["해외"], mode="lines", name="해외")
market_figure.update_layout(title="국내·해외 자산 변화", yaxis_title="원")
render_chart(
    market_figure,
    "국내와 해외 평가자산을 같은 원화 기준으로 비교합니다.",
    filtered,
    key="history-market",
)

st.subheader("날짜별 스냅샷")
st.dataframe(filtered.sort_values("날짜", ascending=False), width="stretch", hide_index=True)
