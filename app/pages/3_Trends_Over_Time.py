import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.lib import charts, queries, ui  # noqa: E402

st.set_page_config(page_title="Trends Over Time", layout="wide", initial_sidebar_state="expanded")
ui.inject_sidebar_toggle_style()
st.title("Trends Over Time")

all_cantons = queries.cantons()
default = ["Zürich", "Genève", "Jura"]
selected_names = st.multiselect(
    "Cantons", options=all_cantons["kt_name_de"].tolist(),
    default=[c for c in default if c in all_cantons["kt_name_de"].tolist()],
)
kt_ids = tuple(all_cantons.loc[all_cantons["kt_name_de"].isin(selected_names), "kt_id"]) if selected_names else None

st.plotly_chart(
    charts.line_trend(
        queries.vacancy_trend(kt_ids), x="year", y="vacancy_rate_pct", color="kt_abbr",
        title="Vacancy rate over time (%)",
    ),
    use_container_width=True,
)

st.plotly_chart(
    charts.line_trend(
        queries.rent_trend(kt_ids), x="year", y="avg_rent_chf", color="kt_abbr",
        title="Average rent over time (CHF/month, all room sizes) -- discrete survey-wave markers, not interpolated",
        markers=True,
    ),
    use_container_width=True,
)
st.caption(
    "Rent points come from the BFS Strukturerhebung, a rolling structural survey, not a monthly "
    "index -- read these as step changes between survey waves, not a smooth trend."
)

st.plotly_chart(
    charts.line_trend(
        queries.population_trend(kt_ids), x="year", y="population_end", color="kt_abbr",
        title="Year-end population over time",
    ),
    use_container_width=True,
)
