import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.lib import charts, scoring, ui  # noqa: E402

st.set_page_config(page_title="Market Tightness Composite", layout="wide", initial_sidebar_state="expanded")
ui.inject_sidebar_toggle_style()
st.title("Market Tightness Composite")

st.warning(
    "This is a heuristic index built for this project, not a validated economic index. "
    "It combines three z-scored signals -- inverted vacancy rate, 5-year population growth, and "
    "average rent level -- using the weights below. Treat it as a starting point for comparison, "
    "not a definitive ranking.",
    icon="⚠️",
)

level = st.radio("Geography", options=["Canton (26)", "District (143)"], horizontal=True)

st.subheader("Weights")
st.caption(
    "Weights don't need to add up to anything in particular -- they're normalized automatically. "
    "Set a weight to 0 to drop that signal entirely."
)
col1, col2, col3 = st.columns(3)
w_vacancy = col1.slider("Vacancy rate (inverted)", 0.0, 3.0, 1.0, 0.1)
w_pop_growth = col2.slider("Population growth", 0.0, 3.0, 1.0, 0.1)
w_rent = col3.slider("Rent level", 0.0, 3.0, 1.0, 0.1)

if w_vacancy == w_pop_growth == w_rent == 0:
    st.error("At least one weight must be above 0.")
    st.stop()

if level == "Canton (26)":
    df = scoring.compute_tightness_index(w_vacancy, w_pop_growth, w_rent)

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

else:
    st.info(
        "BFS doesn't publish rent or population/migration below canton level (see Data Sources & "
        "Caveats), so the population-growth and rent signals here are each district's **parent "
        "canton's** value, shared by every district in that canton. Only vacancy is a genuine "
        "district-level signal -- if you want a purely district-resolution score, set the other "
        "two weights to 0.",
        icon="ℹ️",
    )

    df = scoring.compute_district_tightness_index(w_vacancy, w_pop_growth, w_rent)

    top_n = 15
    tightest = df.head(top_n)
    loosest = df.tail(top_n).sort_values("tightness_score")

    c1, c2 = st.columns(2)
    with c1:
        st.plotly_chart(
            charts.ranked_bar(
                tightest, x="bezirk_name", y="tightness_score",
                title=f"{top_n} tightest districts", color="tightness_score",
            ),
            use_container_width=True,
        )
    with c2:
        st.plotly_chart(
            charts.ranked_bar(
                loosest, x="bezirk_name", y="tightness_score",
                title=f"{top_n} loosest districts", color="tightness_score",
            ),
            use_container_width=True,
        )

    st.subheader("Score components (all 143 districts)")
    st.dataframe(
        df[[
            "bezirk_name", "kt_abbr", "vacancy_rate_pct",
            "z_vacancy_inv", "z_pop_growth_canton_context", "z_rent_canton_context", "tightness_score",
        ]],
        use_container_width=True,
        hide_index=True,
    )
