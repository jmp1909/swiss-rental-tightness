import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.lib import charts, queries, ui  # noqa: E402

st.set_page_config(page_title="Geography Detail", layout="wide", initial_sidebar_state="expanded")
ui.inject_sidebar_toggle_style()
st.title("Geography Detail")

level = st.radio("Geography", options=["Canton", "District"], horizontal=True)

if level == "Canton":
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
    st.plotly_chart(
        charts.line_trend(data["rent"], x="year", y="avg_rent_chf", color="room_count_cat", title=f"{name} -- average rent by room count (CHF)", markers=True),
        use_container_width=True,
    )

    col3, col4 = st.columns(2)
    with col3:
        st.subheader("Migration components")
        mig_df = data["migration"].melt(id_vars="year", value_vars=["immigration", "emigration", "net_migration"], var_name="component", value_name="persons")
        st.plotly_chart(
            charts.line_trend(mig_df, x="year", y="persons", color="component", title=f"{name} -- migration components"),
            use_container_width=True,
        )
    with col4:
        st.subheader("New dwellings constructed")
        st.plotly_chart(
            charts.line_trend(data["new_dwellings"], x="year", y="new_dwellings", color=None, title=f"{name} -- new dwellings per year"),
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
        st.write("New dwellings")
        st.dataframe(data["new_dwellings"], use_container_width=True, hide_index=True)

else:
    all_districts = queries.districts()
    label = st.selectbox("District", options=all_districts["label"].tolist(), index=0)
    row = all_districts.loc[all_districts["label"] == label].iloc[0]
    bezirk_id, bezirk_name, kt_id, kt_name = row["bezirk_id"], row["bezirk_name"], int(row["kt_id"]), row["kt_name_de"]

    st.info(
        f"Only vacancy is genuine district-level data. The other charts below show **{kt_name}'s** "
        "(this district's parent canton) own history as context, since BFS doesn't publish rent, "
        "population, or construction data below canton level -- see Data Sources & Caveats.",
        icon="ℹ️",
    )

    vac_trend = queries.district_vacancy_trend(bezirk_id)
    st.subheader(f"{bezirk_name} -- vacancy rate (district-level, %)")
    if vac_trend["vacancy_rate_pct"].notna().any():
        st.plotly_chart(
            charts.line_trend(vac_trend, x="year", y="vacancy_rate_pct", color=None, title=f"{bezirk_name} -- vacancy rate (%)"),
            use_container_width=True,
        )
    else:
        st.caption("No vacancy data for this district (likely a historical-only code, see Data Sources & Caveats).")

    canton_data = queries.canton_detail(kt_id)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader(f"Context: {kt_name} -- population")
        st.plotly_chart(
            charts.line_trend(canton_data["population"], x="year", y="population_end", color=None, title=f"{kt_name} -- year-end population"),
            use_container_width=True,
        )
    with col2:
        st.subheader(f"Context: {kt_name} -- new dwellings")
        st.plotly_chart(
            charts.line_trend(canton_data["new_dwellings"], x="year", y="new_dwellings", color=None, title=f"{kt_name} -- new dwellings per year"),
            use_container_width=True,
        )

    st.subheader(f"Context: {kt_name} -- rent by room count")
    st.plotly_chart(
        charts.line_trend(canton_data["rent"], x="year", y="avg_rent_chf", color="room_count_cat", title=f"{kt_name} -- average rent by room count (CHF)", markers=True),
        use_container_width=True,
    )

    with st.expander("Raw tables"):
        st.write("Vacancy (this district)")
        st.dataframe(vac_trend, use_container_width=True, hide_index=True)
        st.write(f"Population (context: {kt_name})")
        st.dataframe(canton_data["population"], use_container_width=True, hide_index=True)
        st.write(f"Rent (context: {kt_name})")
        st.dataframe(canton_data["rent"], use_container_width=True, hide_index=True)
        st.write(f"New dwellings (context: {kt_name})")
        st.dataframe(canton_data["new_dwellings"], use_container_width=True, hide_index=True)
