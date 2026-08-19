import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.lib import charts, scoring  # noqa: E402

st.set_page_config(page_title="Market Tightness Composite", layout="wide")
st.title("Market Tightness Composite")

st.warning(
    "This is a heuristic index built for this project, not a validated economic index. "
    "It z-scores and averages three signals: inverted vacancy rate, 5-year population growth, "
    "and average rent level, each for that canton's own latest available year. Treat it as a "
    "starting point for comparison, not a definitive ranking.",
    icon="⚠️",
)

df = scoring.compute_tightness_index()

st.plotly_chart(
    charts.ranked_bar(
        df, x="kt_abbr", y="tightness_score",
        title="Cantons ranked by composite tightness score (higher = tighter market)",
        color="tightness_score",
    ),
    use_container_width=True,
)

st.subheader("Score components")
st.dataframe(
    df[[
        "kt_abbr", "kt_name_de", "vacancy_rate_pct", "pop_growth_5y_pct", "avg_rent_chf",
        "z_vacancy_inv", "z_pop_growth", "z_rent", "tightness_score",
    ]],
    use_container_width=True,
    hide_index=True,
)
