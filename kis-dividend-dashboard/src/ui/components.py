"""Reusable accessible Streamlit presentation components."""

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.ui.formatting import kst_datetime
from src.ui.viewmodels import MetricView, SourceView, SyncView


def render_metric_grid(metrics: tuple[MetricView, ...]) -> None:
    """Render responsive metric cards with explicit status labels."""
    cards: list[str] = []
    for metric in metrics:
        delta = f'<div class="kd-delta">{escape(metric.delta)}</div>' if metric.delta else ""
        help_text = (
            f'<div class="kd-meta">{escape(metric.help_text)}</div>' if metric.help_text else ""
        )
        cards.append(
            '<section class="kd-metric-card">'
            f'<div><span class="kd-badge kd-{metric.kind}">{_kind_label(metric.kind)}</span></div>'
            f'<div class="kd-metric-label">{escape(metric.label)}</div>'
            f'<div class="kd-metric-value">{escape(metric.value)}</div>{delta}{help_text}</section>'
        )
    st.markdown(f'<div class="kd-metric-grid">{"".join(cards)}</div>', unsafe_allow_html=True)


def render_sync_status(sync: SyncView) -> None:
    """Render a sanitized synchronization summary and failure list."""
    state_label, css = {
        "success": ("전체 성공", "success"),
        "partial": ("부분 성공", "warning"),
        "failed": ("실패", "error"),
        "idle": ("대기", ""),
        "running": ("동기화 중", ""),
    }[sync.state]
    token_label = {
        "reused": "기존 토큰 재사용",
        "issued": "신규 토큰 발급",
        "not_used": "토큰 미사용",
    }[sync.token_action]
    st.markdown(
        f'<div class="kd-status kd-status-{css}" role="status"><strong>{state_label}</strong> · '
        f'{escape(sync.message)}<br><span class="kd-meta">마지막 정상 동기화: '
        f"{kst_datetime(sync.last_success_at)} · {token_label} · "
        f"저장 {sync.inserted}건 · 수정 {sync.updated}건</span></div>",
        unsafe_allow_html=True,
    )
    if sync.failures:
        with st.expander("실패 항목 보기"):
            for failure in sync.failures:
                st.write(f"- {failure}")


def render_source(source: SourceView) -> None:
    """Render source provenance, freshness, and fallback state."""
    realtime = "실시간" if source.is_realtime else "비실시간"
    fallback = " · 마지막 저장값 사용" if source.using_last_saved else ""
    st.markdown(
        f'<div class="kd-source">출처: {escape(source.source)} · '
        f"기준: {kst_datetime(source.as_of)} · "
        f"조회: {kst_datetime(source.fetched_at)} · {realtime}{fallback}</div>",
        unsafe_allow_html=True,
    )


def render_chart(figure: go.Figure, summary: str, table: pd.DataFrame, *, key: str) -> None:
    """Render a responsive chart with a text summary and table fallback."""
    figure.update_layout(autosize=True, margin={"l": 16, "r": 16, "t": 48, "b": 24})
    st.plotly_chart(
        figure,
        width="stretch",
        key=key,
        config={"displaylogo": False, "responsive": True, "scrollZoom": False},
    )
    st.caption(summary)
    with st.expander("차트 데이터를 표로 보기"):
        st.dataframe(table, width="stretch", hide_index=True)


def empty_state(title: str, guidance: str) -> None:
    """Render an actionable empty-state message."""
    st.info(f"{title}\n\n{guidance}")


def _kind_label(kind: str) -> str:
    return {"actual": "실제", "confirmed": "확정", "estimated": "예상", "neutral": "현황"}[kind]
