"""Monthly dividend event calendar page."""

# ruff: noqa: N999

import pandas as pd
import streamlit as st
from src.ui.auth import require_authentication
from src.ui.components import empty_state, render_source
from src.ui.data_access import calendar_view
from src.ui.shell import render_page_header, render_sync_action

if not require_authentication():
    st.stop()

is_demo = render_page_header(
    "배당 캘린더", "배당락일·기준일·지급일과 예상 지급일을 월별로 확인합니다."
)
render_sync_action(is_demo=is_demo)
data = calendar_view(is_demo=is_demo)
render_source(data.source)
events = data.events.rename(
    columns={
        "event_date": "날짜",
        "symbol": "종목",
        "event_type": "이벤트",
        "status": "상태",
    }
).copy()

if events.empty:
    empty_state("표시할 배당 일정이 없습니다.", "배당 이벤트를 동기화하거나 이력을 가져와 주세요.")
    st.stop()

events["날짜"] = pd.to_datetime(events["날짜"])
events["month"] = events["날짜"].dt.to_period("M").astype(str)
month = st.selectbox("월", sorted(events["month"].unique().tolist(), reverse=True))
event_types = st.multiselect(
    "일정 유형",
    sorted(events["이벤트"].unique().tolist()),
    default=sorted(events["이벤트"].unique().tolist()),
)
filtered = events.loc[(events["month"] == month) & events["이벤트"].isin(event_types)]

st.subheader(f"{month} 일정")
if filtered.empty:
    empty_state("선택한 조건의 일정이 없습니다.", "일정 유형 필터를 변경해 주세요.")
else:
    for event_date, day_events in filtered.groupby(filtered["날짜"].dt.date, sort=True):
        with st.expander(f"{event_date.isoformat()} · {len(day_events)}건", expanded=True):
            st.dataframe(
                day_events.drop(columns=["month"]),
                width="stretch",
                hide_index=True,
            )

undated = events.loc[events["날짜"].isna()]
if not undated.empty:
    with st.expander("날짜 미정 이벤트"):
        st.dataframe(undated.drop(columns=["month"]), width="stretch", hide_index=True)
