import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.lib import queries  # noqa: E402

st.set_page_config(page_title="Swiss Rental Market Tightness", layout="wide")

st.title("Swiss Rental Market Tightness / Vacancy Risk Dashboard")
st.caption(
    "Built on official BFS (Federal Statistical Office) cantonal data: vacancy rate, "
    "rent levels, and population/migration. Use the sidebar to navigate."
)

vac = queries.vacancy_latest()
pop = queries.population_latest()
rent = queries.rent_latest()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Cantons covered", f"{len(queries.cantons())}/26")
col2.metric("Latest vacancy data year", int(vac["year"].max()))
col3.metric("Latest rent survey year", int(rent["year"].max()))
col4.metric("Latest population year", int(pop["year"].max()))

st.markdown(
    """
### Pages
- **Cantonal Overview** — latest vacancy rate by canton, on a map and in a sortable table.
- **Market Tightness Composite** — a heuristic ranking combining vacancy, population growth, and rent.
- **Trends Over Time** — per-canton time series for vacancy, rent, and population.
- **Canton Detail** — full drill-down into one canton across every loaded metric.
- **Data Sources & Caveats** — exactly where every number comes from, and where the limits are.
"""
)

st.info(
    "This is a portfolio/analysis project built entirely on public BFS open data. "
    "See the Data Sources & Caveats page before drawing conclusions from any single number.",
    icon="ℹ️",
)
