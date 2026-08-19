import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from app.lib import charts, scoring, ui  # noqa: E402

st.set_page_config(page_title="Market Tightness Composite", layout="wide", initial_sidebar_state="expanded")
ui.inject_sidebar_toggle_style()
st.title("Market Tightness Composite")

st.warning(
    "This is a heuristic index built for this project, not a validated economic index. It "
    "combines four normalized signals -- inverted vacancy, a population-growth-vs-new-construction "
    "demand/supply gap, rent level, and rent growth -- using the weights and method below. Treat it "
    "as a starting point for comparison, not a definitive ranking.",
    icon="⚠️",
)

level = st.radio("Geography", options=["Canton (26)", "District (143)"], horizontal=True)

METHOD_HELP = {
    "zscore": "Standard deviations from the mean. Standard, but one extreme canton/district can pull "
              "everyone else's score around.",
    "percentile": "Rank-based (0-100th percentile, recentred). Robust to a single outlier, but "
                  "discards how *far* apart geographies actually are.",
}

st.subheader("Normalization method")
st.caption(
    "z-score and percentile rank can genuinely disagree, especially with only 26 cantons -- pick "
    "independently for each geography level to compare."
)
# A widget that's only rendered in one branch of an if/else doesn't reliably
# keep its value in Streamlit when that branch isn't taken -- so the "current
# choice per level" is tracked explicitly here instead of trusting the
# widget's own key-based persistence across runs where it isn't rendered.
st.session_state.setdefault("tightness_method_canton", "zscore")
st.session_state.setdefault("tightness_method_district", "zscore")
state_key = "tightness_method_canton" if level == "Canton (26)" else "tightness_method_district"

method = st.radio(
    f"Method for {level}", options=list(scoring.NORMALIZATION_METHODS),
    horizontal=True,
    index=scoring.NORMALIZATION_METHODS.index(st.session_state[state_key]),
    captions=[METHOD_HELP[m] for m in scoring.NORMALIZATION_METHODS],
    key=f"method_widget_{state_key}",
)
st.session_state[state_key] = method

st.subheader("Weights")
st.caption(
    "Weights don't need to add up to anything in particular -- they're normalized automatically. "
    "Set a weight to 0 to drop that signal entirely."
)
col1, col2, col3, col4 = st.columns(4)
w_vacancy = col1.slider("Vacancy (inverted)", 0.0, 3.0, 1.0, 0.1)
w_demand_supply = col2.slider("Demand/supply gap", 0.0, 3.0, 1.0, 0.1)
w_rent_level = col3.slider("Rent level", 0.0, 3.0, 1.0, 0.1)
w_rent_growth = col4.slider("Rent growth (5y)", 0.0, 3.0, 1.0, 0.1)

if w_vacancy == w_demand_supply == w_rent_level == w_rent_growth == 0:
    st.error("At least one weight must be above 0.")
    st.stop()

if level == "Canton (26)":
    df = scoring.compute_tightness_index(w_vacancy, w_demand_supply, w_rent_level, w_rent_growth, method=method)

    st.plotly_chart(
        charts.ranked_bar(
            df, x="kt_abbr", y="tightness_score",
            title="Cantons ranked by composite tightness score (higher = tighter market)",
            color="tightness_score",
        ),
        width='stretch',
    )

    st.subheader("Score components")
    st.dataframe(
        df[[
            "kt_abbr", "kt_name_de", "vacancy_rate_pct", "pop_growth_5y_pct",
            "avg_rent_chf", "rent_growth_5y_pct",
            "z_vacancy_inv", "z_demand_supply_gap", "z_rent_level", "z_rent_growth", "tightness_score",
        ]],
        width='stretch',
        hide_index=True,
    )

else:
    st.info(
        "BFS doesn't publish rent, population, or construction data below canton level (see Data "
        "Sources & Caveats), so the demand/supply, rent-level, and rent-growth signals here are each "
        "district's **parent canton's** value, shared by every district in that canton. Only vacancy "
        "is a genuine district-level signal -- if you want a purely district-resolution score, set "
        "the other three weights to 0.",
        icon="ℹ️",
    )

    df = scoring.compute_district_tightness_index(w_vacancy, w_demand_supply, w_rent_level, w_rent_growth, method=method)

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
            width='stretch',
        )
    with c2:
        st.plotly_chart(
            charts.ranked_bar(
                loosest, x="bezirk_name", y="tightness_score",
                title=f"{top_n} loosest districts", color="tightness_score",
            ),
            width='stretch',
        )

    st.subheader("Score components (all 143 districts)")
    st.dataframe(
        df[[
            "bezirk_name", "kt_abbr", "vacancy_rate_pct", "z_vacancy_inv",
            "z_demand_supply_gap_canton_context", "z_rent_level_canton_context",
            "z_rent_growth_canton_context", "tightness_score",
        ]],
        width='stretch',
        hide_index=True,
    )
