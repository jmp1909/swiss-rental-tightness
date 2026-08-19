import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.lib import charts, queries  # noqa: E402

st.set_page_config(page_title="Canton Detail", layout="wide")
st.title("Canton Detail")

st.caption(
    "Vacancy is shown down to district (Bezirk) level below -- 155 districts nationally, a stable "
    "geography with no commune-merger tracking needed. Full municipality-level vacancy (~2000 "
    "communes) is confirmed available in the same source but not loaded, since Swiss municipalities "
    "merge often enough that a proper municipality dimension needs merger-aware historization -- a "
    "separate piece of work from the data pull itself. See Data Sources & Caveats for the detail."
)

all_cantons = queries.cantons()
name = st.selectbox("Canton", options=all_cantons["kt_name_de"].tolist(), index=0)
kt_id = int(all_cantons.loc[all_cantons["kt_name_de"] == name, "kt_id"].iloc[0])

data = queries.canton_detail(kt_id)

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(
        charts.line_trend(data["vacancy"], x="year", y="vacancy_rate_pct", color=None, title=f"{name} -- vacancy rate (%)"),
        use_container_width=True,
    )
with col2:
    st.plotly_chart(
        charts.line_trend(data["population"], x="year", y="population_end", color=None, title=f"{name} -- year-end population"),
        use_container_width=True,
    )

st.subheader("Vacancy rate by district")
district_df = queries.district_vacancy_latest(kt_id)
if district_df.empty:
    st.caption("No district-level data for this canton.")
else:
    latest_district_year = int(district_df["year"].max())
    st.plotly_chart(
        charts.ranked_bar(
            district_df, x="bezirk_name", y="vacancy_rate_pct",
            title=f"{name} -- vacancy rate by district ({latest_district_year}, %)",
            color="vacancy_rate_pct",
        ),
        use_container_width=True,
    )

st.subheader("Rent by room count")
rent_df = data["rent"]
st.plotly_chart(
    charts.line_trend(rent_df, x="year", y="avg_rent_chf", color="room_count_cat", title=f"{name} -- average rent by room count (CHF)", markers=True),
    use_container_width=True,
)

st.subheader("Migration components")
mig_df = data["migration"].melt(id_vars="year", value_vars=["immigration", "emigration", "net_migration"], var_name="component", value_name="persons")
st.plotly_chart(
    charts.line_trend(mig_df, x="year", y="persons", color="component", title=f"{name} -- migration components"),
    use_container_width=True,
)

with st.expander("Raw tables"):
    st.write("Vacancy (canton)")
    st.dataframe(data["vacancy"], use_container_width=True, hide_index=True)
    st.write("Vacancy (district, latest year)")
    st.dataframe(district_df, use_container_width=True, hide_index=True)
    st.write("Rent")
    st.dataframe(data["rent"], use_container_width=True, hide_index=True)
    st.write("Population")
    st.dataframe(data["population"], use_container_width=True, hide_index=True)
    st.write("Migration")
    st.dataframe(data["migration"], use_container_width=True, hide_index=True)
