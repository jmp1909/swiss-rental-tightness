import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.lib import queries, ui  # noqa: E402

st.set_page_config(page_title="Data Sources & Caveats", layout="wide", initial_sidebar_state="expanded")
ui.inject_sidebar_toggle_style()
st.title("Data Sources & Caveats")

audit_path = Path(__file__).resolve().parent.parent.parent / "DATA_AUDIT.md"
st.markdown(audit_path.read_text(encoding="utf-8"))

st.subheader("Ingestion log (this warehouse)")
st.caption("Every ingestion run appends a row here -- source, resource URL, rows loaded, status.")
st.dataframe(queries.ingest_log(), width='stretch', hide_index=True)
