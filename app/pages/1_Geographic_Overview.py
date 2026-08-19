import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.lib import charts, queries, ui  # noqa: E402

st.set_page_config(page_title="Geographic Overview", layout="wide", initial_sidebar_state="expanded")
ui.inject_sidebar_toggle_style()
st.title("Geographic Overview")

vac = queries.vacancy_latest()
rent = queries.rent_latest()
pop = queries.population_latest()

level = st.radio(
    "Map granularity", options=["Canton (26)", "District (143)"], horizontal=True,
)

if level == "Canton (26)":
    st.plotly_chart(
        charts.choropleth(
            vac, value_col="vacancy_rate_pct", id_col="kt_id",
            title=f"Vacancy rate by canton ({int(vac['year'].max())}, %)",
            color_scale="RdYlGn_r", label="Vacancy %", level="canton",
            hover_name_col="kt_name_de",
        ),
        width='stretch',
    )
else:
    dist = queries.district_vacancy_latest_all()
    st.plotly_chart(
        charts.choropleth(
            dist, value_col="vacancy_rate_pct", id_col="bezirk_id",
            title=f"Vacancy rate by district ({int(dist['year'].max())}, %)",
            color_scale="RdYlGn_r", label="Vacancy %", level="district",
            hover_name_col="bezirk_name",
        ),
        width='stretch',
    )
    st.caption(
        "143 of 155 known districts have current data -- the rest are 'Bezirksfreies Gebiet' "
        "placeholder codes (land not assigned to any district in that canton), not former "
        "districts, and don't have boundary geometry of their own."
    )

st.subheader("Combined latest snapshot")
table = (
    vac[["kt_abbr", "kt_name_de", "year", "vacancy_rate_pct", "vacant_count"]]
    .rename(columns={"year": "vacancy_year"})
    .merge(
        rent[["kt_abbr", "year", "avg_rent_chf"]].rename(columns={"year": "rent_year"}),
        on="kt_abbr", how="left",
    )
    .merge(
        pop[["kt_abbr", "year", "population_end", "pop_growth_5y_pct"]].rename(columns={"year": "population_year"}),
        on="kt_abbr", how="left",
    )
    .sort_values("vacancy_rate_pct", ascending=False)
)
st.dataframe(table, width='stretch', hide_index=True)
st.caption(
    "Each metric uses that source's own latest available year -- vacancy, rent, and population "
    "surveys don't all publish on the same schedule. See Data Sources & Caveats."
)
