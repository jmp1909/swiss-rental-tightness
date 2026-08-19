"""Shared UI tweaks applied on every page."""
import streamlit as st

_SIDEBAR_TOGGLE_CSS = """
<style>
[data-testid="stExpandSidebarButton"],
[data-testid="stSidebar"] [data-testid="stBaseButton-headerNoPadding"] {
    width: 3rem;
    height: 3rem;
    background-color: rgba(120, 120, 255, 0.18);
    border-radius: 0.5rem;
    border: 1px solid rgba(120, 120, 255, 0.5);
}
[data-testid="stExpandSidebarButton"] svg,
[data-testid="stSidebar"] [data-testid="stBaseButton-headerNoPadding"] svg {
    width: 1.75rem;
    height: 1.75rem;
}
</style>
"""


def inject_sidebar_toggle_style() -> None:
    """Make the sidebar open/close arrow (top-left) bigger and higher-contrast,
    since it's the only way to reach the other pages when the sidebar is
    collapsed (narrow viewports, or after a user manually collapses it)."""
    st.markdown(_SIDEBAR_TOGGLE_CSS, unsafe_allow_html=True)
