"""Authenticated Streamlit application router."""

import streamlit as st
from src.logging_config import configure_logging
from src.ui.auth import require_authentication
from src.ui.home import render_home
from src.ui.responsive import apply_responsive_styles

st.set_page_config(
    page_title="한국투자 잔고·배당금",
    page_icon=None,
    layout="wide",
    initial_sidebar_state="collapsed",
)
configure_logging()
apply_responsive_styles()


def home_page() -> None:
    """Render the authenticated home page."""
    render_home()


authenticated = require_authentication()
application_pages = [
    st.Page(home_page, title="홈", default=True),
    st.Page("pages/1_portfolio.py", title="잔고"),
    st.Page("pages/2_dividends.py", title="배당"),
    st.Page("pages/3_calendar.py", title="배당 캘린더"),
    st.Page("pages/4_history.py", title="자산 이력"),
    st.Page("pages/5_settings.py", title="설정"),
]
st.session_state["navigation_pages"] = tuple(application_pages)
login_page = st.Page(lambda: None, title="로그인", default=True)
navigation = st.navigation(
    application_pages if authenticated else [login_page],
    position="top" if authenticated else "hidden",
)
if not authenticated:
    st.stop()
navigation.run()
