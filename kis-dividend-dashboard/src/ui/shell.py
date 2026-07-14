"""Shared authenticated page shell."""

import streamlit as st

from src.ui.auth import demo_mode, logout
from src.ui.data_access import synchronize
from src.ui.viewmodels import SyncView


def render_page_header(title: str, subtitle: str) -> bool:
    """Render title, logout action, and demo disclosure."""
    is_demo = demo_mode()
    heading, action = st.columns([5, 1], vertical_alignment="center")
    with heading:
        st.title(title)
        st.caption(subtitle)
    with action:
        if st.button("로그아웃", width="stretch"):
            logout()
            st.rerun()
    with st.container(key="mobile_nav"), st.expander("메뉴 열기"):
        first_row = st.columns(3)
        second_row = st.columns(3)
        columns = (*first_row, *second_row)
        navigation_pages = st.session_state.get("navigation_pages", ())
        for column, target in zip(columns, navigation_pages, strict=False):
            with column:
                st.page_link(target, label=target.title, width="stretch")
    if is_demo:
        st.warning("DEMO_MODE · 가상 데이터입니다.")
    return is_demo


def render_sync_action(*, is_demo: bool) -> SyncView | None:
    """Run one guarded synchronization and return its safe result."""
    if "sync_in_progress" not in st.session_state:
        st.session_state.sync_in_progress = False
    clicked = st.button(
        "지금 동기화",
        type="primary",
        disabled=bool(st.session_state.sync_in_progress),
        width="stretch",
    )
    if not clicked:
        return None
    st.session_state.sync_in_progress = True
    with st.status("잔고와 배당 데이터를 동기화하고 있습니다.", expanded=True) as status:
        result = synchronize(is_demo=is_demo)
        status.update(label=result.message, state="complete", expanded=False)
    st.session_state.sync_in_progress = False
    st.cache_data.clear()
    return result
