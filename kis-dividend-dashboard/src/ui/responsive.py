"""Responsive styles limited to application-owned classes."""

import streamlit as st


def apply_responsive_styles() -> None:
    """Install metric, status, and reduced-motion styles."""
    st.markdown(
        """
        <style>
        :root {
          color-scheme: light dark;
          --kd-blue: #1d4ed8; --kd-green: #047857; --kd-purple: #6d28d9;
          --kd-amber: #b45309; --kd-red: #b91c1c;
        }
        .kd-metric-grid {
          display: grid; gap: 0.75rem;
          grid-template-columns: repeat(4, minmax(0, 1fr));
          margin: 0.5rem 0 1.5rem;
        }
        .kd-metric-card {
          min-width: 0; padding: 1rem; border: 1px solid rgba(128,128,128,.28);
          border-radius: .75rem; background: rgba(128,128,128,.06);
        }
        .kd-metric-label, .kd-meta { color: rgba(110,110,110,.98); font-size: .82rem; }
        .kd-metric-value {
          margin-top: .35rem; font-size: clamp(1.2rem, 3vw, 1.8rem);
          font-weight: 700; line-height: 1.2; font-variant-numeric: tabular-nums;
          overflow-wrap: anywhere;
        }
        .kd-delta { margin-top: .35rem; font-size: .82rem; }
        .kd-badge {
          display: inline-flex; align-items: center; padding: .15rem .48rem;
          border-radius: 999px; border: 1px solid currentColor; font-size: .72rem;
          font-weight: 650; line-height: 1.35;
        }
        .kd-actual { color: var(--kd-blue); background: #dbeafe; }
        .kd-confirmed { color: var(--kd-green); background: #d1fae5; }
        .kd-estimated { color: var(--kd-purple); background: #ede9fe; }
        .kd-neutral { color: #3f3f46; background: #e4e4e7; }
        .kd-status {
          padding: .8rem 1rem; border-left: .3rem solid var(--kd-blue); margin-bottom: 1rem;
        }
        .kd-status-warning { border-left-color: var(--kd-amber); }
        .kd-status-error { border-left-color: var(--kd-red); }
        .kd-status-success { border-left-color: var(--kd-green); }
        .kd-source, .kd-meta, .kd-status, [data-testid="stAlert"] {
          word-break: keep-all; overflow-wrap: normal;
        }
        .kd-source { font-size: .82rem; color: rgba(110,110,110,.98); margin: .4rem 0 1rem; }
        .st-key-mobile_nav { display: none; }
        @media (max-width: 1199px) {
            .kd-metric-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 600px) {
          div[data-testid="stButton"] button, [role="tab"],
          button[data-testid^="stNumberInputStep"] {
            min-height: 44px !important; height: auto !important;
          }
          [role="tablist"] { flex-wrap: wrap; row-gap: .25rem; }
          .st-key-mobile_nav { display: block; margin: 0 0 1rem; }
          .st-key-mobile_nav [data-testid="stHorizontalBlock"] { gap: .35rem; }
          .st-key-mobile_nav [data-testid="stPageLink"] a {
            display: flex; align-items: center; justify-content: center;
            min-height: 44px; padding: .4rem; border: 1px solid rgba(128,128,128,.35);
            border-radius: .55rem; text-decoration: none; color: inherit;
            font-size: .85rem; font-weight: 650; word-break: keep-all;
          }
        }
        @media (max-width: 359px) { .kd-metric-grid { grid-template-columns: 1fr; } }
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after { scroll-behavior: auto !important; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
