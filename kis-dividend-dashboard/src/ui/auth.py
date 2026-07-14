"""Session-scoped password authentication gate."""

import os
import time
from datetime import UTC, datetime, timedelta
from typing import Final

import streamlit as st
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError
from streamlit.errors import StreamlitSecretNotFoundError

from src.config import Settings

AUTHENTICATED: Final = "authenticated"
LAST_ACTIVITY: Final = "last_activity_at"
FAILED_ATTEMPTS: Final = "failed_login_attempts"
PASSWORD_HASHER: Final = PasswordHasher()


def secret_value(name: str, default: str = "") -> str:
    """Read a server-side secret without exposing it to page state."""
    settings = Settings()
    local_values = {
        "APP_PASSWORD_HASH": settings.APP_PASSWORD_HASH.get_secret_value(),
        "DEMO_MODE": str(settings.DEMO_MODE).lower(),
        "SESSION_TIMEOUT_MINUTES": str(settings.SESSION_TIMEOUT_MINUTES),
    }
    fallback = local_values.get(name, os.getenv(name, default))
    try:
        value = st.secrets.get(name, fallback)
    except StreamlitSecretNotFoundError:
        value = fallback
    return str(value)


def demo_mode() -> bool:
    """Return whether isolated sample data is enabled."""
    return secret_value("DEMO_MODE", "false").strip().lower() == "true"


def require_authentication() -> bool:
    """Render the login gate and return the authorization state."""
    if _session_is_active():
        st.session_state[LAST_ACTIVITY] = datetime.now(UTC)
        return True
    _clear_authentication()
    _render_login()
    return False


def logout() -> None:
    """Clear the authenticated session."""
    _clear_authentication()


def _session_is_active() -> bool:
    if not bool(st.session_state.get(AUTHENTICATED, False)):
        return False
    last_activity = st.session_state.get(LAST_ACTIVITY)
    if not isinstance(last_activity, datetime):
        return False
    timeout = timedelta(minutes=int(secret_value("SESSION_TIMEOUT_MINUTES", "30")))
    return datetime.now(UTC) - last_activity <= timeout


def _render_login() -> None:
    st.title("한국투자 잔고·배당금 대시보드")
    st.caption("개인용 조회 전용 서비스입니다. 로그인 전에는 계좌 데이터를 조회하지 않습니다.")
    password_hash = secret_value("APP_PASSWORD_HASH")
    if not password_hash:
        st.error("APP_PASSWORD_HASH가 설정되지 않아 로그인할 수 없습니다.")
        return
    with st.form("login-form", clear_on_submit=True):
        password = st.text_input("비밀번호", type="password", autocomplete="current-password")
        submitted = st.form_submit_button("로그인", type="primary", width="stretch")
    if not submitted:
        return
    verified = False
    try:
        verified = PASSWORD_HASHER.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        verified = False
    if verified:
        st.session_state[AUTHENTICATED] = True
        st.session_state[LAST_ACTIVITY] = datetime.now(UTC)
        st.session_state[FAILED_ATTEMPTS] = 0
        st.rerun()
    attempts = int(st.session_state.get(FAILED_ATTEMPTS, 0)) + 1
    st.session_state[FAILED_ATTEMPTS] = attempts
    time.sleep(min(attempts, 3))
    st.error("로그인에 실패했습니다. 비밀번호를 확인해 주세요.")


def _clear_authentication() -> None:
    st.session_state[AUTHENTICATED] = False
    st.session_state.pop(LAST_ACTIVITY, None)
