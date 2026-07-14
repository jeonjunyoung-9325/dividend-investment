"""Authenticated home dashboard composition."""

import plotly.graph_objects as go
import streamlit as st

from src.ui.components import render_chart, render_metric_grid, render_source, render_sync_status
from src.ui.data_access import dashboard_view
from src.ui.shell import render_page_header, render_sync_action


def render_home() -> None:
    """Render summary cards and evidence-backed charts."""
    is_demo = render_page_header("홈", "자산과 배당 현금흐름을 한눈에 확인합니다.")
    data = dashboard_view(is_demo=is_demo)
    sync_result = render_sync_action(is_demo=is_demo)
    render_sync_status(sync_result or data.sync)
    render_source(data.source)
    render_metric_grid(data.metrics)

    st.subheader("핵심 추세")
    asset_figure = go.Figure(
        go.Scatter(
            x=data.asset_history["날짜"],
            y=data.asset_history["총 평가자산"],
            mode="lines",
            name="총 평가자산",
        )
    )
    asset_figure.update_layout(title="일별 총 평가자산 변화", yaxis_title="원")
    render_chart(
        asset_figure,
        "선택 기간의 원화 환산 총 평가자산 추세입니다.",
        data.asset_history,
        key="home-assets",
    )

    dividend_figure = go.Figure()
    dividend_figure.add_bar(
        x=data.monthly_dividends["월"], y=data.monthly_dividends["실제"], name="실제"
    )
    dividend_figure.add_bar(
        x=data.monthly_dividends["월"], y=data.monthly_dividends["확정"], name="확정"
    )
    dividend_figure.add_bar(
        x=data.monthly_dividends["월"], y=data.monthly_dividends["예상"], name="예상"
    )
    dividend_figure.update_layout(
        title="월별 실제·확정·예상 배당금", barmode="group", yaxis_title="원"
    )
    st.caption("예상 지급월은 규칙적인 지급 주기가 확인된 종목만 표시합니다.")
    render_chart(
        dividend_figure,
        "실제 입금, 자격이 확인된 확정 예정, 과거 이력 기반 예상 금액을 분리한 월별 합계입니다.",
        data.monthly_dividends,
        key="home-dividends",
    )

    assets_tab, dividends_tab = st.tabs(["자산 구성", "배당 분석"])
    with assets_tab:
        allocation = go.Figure(
            go.Pie(labels=data.allocation["시장"], values=data.allocation["평가금액"], hole=0.55)
        )
        allocation.update_layout(title="국내·해외 자산 비중")
        render_chart(
            allocation,
            "국내와 해외의 원화 환산 평가금액 비중입니다.",
            data.allocation,
            key="allocation",
        )
        position_weights = go.Figure(
            go.Bar(
                x=data.position_weights["원화 평가금액"],
                y=data.position_weights["종목명"],
                orientation="h",
            )
        )
        position_weights.update_layout(title="종목별 평가금액 비중")
        render_chart(
            position_weights,
            "평가금액 상위 종목을 내림차순으로 표시합니다.",
            data.position_weights,
            key="position-weights",
        )
    with dividends_tab:
        contributions = go.Figure(
            go.Bar(
                x=data.dividend_contributions["예상 배당금"],
                y=data.dividend_contributions["종목명"],
                orientation="h",
            )
        )
        contributions.update_layout(title="종목별 예상 배당 기여도")
        render_chart(
            contributions,
            "향후 12개월 예상 세전 배당금에 대한 종목별 기여도입니다.",
            data.dividend_contributions,
            key="dividend-contributions",
        )
        cumulative = go.Figure(
            go.Scatter(
                x=data.cumulative_dividends["월"],
                y=data.cumulative_dividends["누적 실수령"],
                mode="lines",
                name="누적 실수령",
            )
        )
        cumulative.update_layout(title="누적 실수령 배당금", yaxis_title="원")
        render_chart(
            cumulative,
            "실제 계좌에 입금된 세후 배당금의 누적 합계입니다.",
            data.cumulative_dividends,
            key="cumulative-dividends",
        )
