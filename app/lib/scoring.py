"""Composite 'market tightness' heuristic: not a validated economic index,
just a transparent, adjustable combination of signals so geographies can be
ranked on one axis. Higher score = tighter (more landlord-favorable) market.

score = ( w_vacancy * z(-vacancy_rate)
        + w_pop_growth * z(pop_growth_5y_pct)
        + w_rent * z(avg_rent_chf) ) / (w_vacancy + w_pop_growth + w_rent)

Weights don't need to sum to 1 -- they're normalized by their own sum, so
setting a weight to 0 drops that signal entirely, and relative size is all
that matters (w=2 counts twice as much as w=1).

Cantons get all three signals from real cantonal-grain sources. Districts
(Bezirke) only have a real district-grain signal for vacancy -- BFS doesn't
publish rent or population/migration below canton level (see DATA_AUDIT.md).
So the district score uses each district's own vacancy rate, but borrows its
*parent canton's* rent and population-growth z-scores as shared context for
every district in that canton. This is flagged explicitly in the returned
columns (suffixed `_canton_context`) and in the app -- it is not a silent
approximation.
"""
import pandas as pd

from . import queries


def _zscore(s: pd.Series) -> pd.Series:
    return (s - s.mean()) / s.std(ddof=0)


def _weighted_score(z_cols: dict[str, tuple[pd.Series, float]]) -> pd.Series:
    total_weight = sum(w for _, w in z_cols.values())
    if total_weight == 0:
        raise ValueError("At least one weight must be non-zero.")
    weighted_sum = sum(z * w for z, w in z_cols.values())
    return weighted_sum / total_weight


def compute_tightness_index(w_vacancy: float = 1.0, w_pop_growth: float = 1.0, w_rent: float = 1.0) -> pd.DataFrame:
    vac = queries.vacancy_latest()[["kt_id", "kt_abbr", "kt_name_de", "vacancy_rate_pct"]]
    pop = queries.population_latest()[["kt_id", "pop_growth_5y_pct"]]
    rent = queries.rent_latest()[["kt_id", "avg_rent_chf"]]

    df = vac.merge(pop, on="kt_id", how="left").merge(rent, on="kt_id", how="left")

    df["z_vacancy_inv"] = -_zscore(df["vacancy_rate_pct"])
    df["z_pop_growth"] = _zscore(df["pop_growth_5y_pct"])
    df["z_rent"] = _zscore(df["avg_rent_chf"])
    df["tightness_score"] = _weighted_score({
        "vacancy": (df["z_vacancy_inv"], w_vacancy),
        "pop_growth": (df["z_pop_growth"], w_pop_growth),
        "rent": (df["z_rent"], w_rent),
    })

    return df.sort_values("tightness_score", ascending=False).reset_index(drop=True)


def compute_district_tightness_index(w_vacancy: float = 1.0, w_pop_growth: float = 1.0, w_rent: float = 1.0) -> pd.DataFrame:
    dist = queries.district_vacancy_latest_all()[["bezirk_id", "bezirk_name", "kt_abbr", "vacancy_rate_pct"]]

    # Canton-level z-scores, computed once across all 26 cantons (the correct
    # reference population for "how tight is this canton relative to other
    # cantons"), then broadcast down to every district in that canton.
    canton_pop = queries.population_latest()[["kt_abbr", "pop_growth_5y_pct"]].copy()
    canton_rent = queries.rent_latest()[["kt_abbr", "avg_rent_chf"]].copy()
    canton_pop["z_pop_growth_canton_context"] = _zscore(canton_pop["pop_growth_5y_pct"])
    canton_rent["z_rent_canton_context"] = _zscore(canton_rent["avg_rent_chf"])

    df = (
        dist
        .merge(canton_pop[["kt_abbr", "z_pop_growth_canton_context"]], on="kt_abbr", how="left")
        .merge(canton_rent[["kt_abbr", "z_rent_canton_context"]], on="kt_abbr", how="left")
    )

    # District's own vacancy, z-scored across all 143 districts -- this is
    # the one genuinely district-resolution signal in the score.
    df["z_vacancy_inv"] = -_zscore(df["vacancy_rate_pct"])

    df["tightness_score"] = _weighted_score({
        "vacancy": (df["z_vacancy_inv"], w_vacancy),
        "pop_growth": (df["z_pop_growth_canton_context"], w_pop_growth),
        "rent": (df["z_rent_canton_context"], w_rent),
    })

    return df.sort_values("tightness_score", ascending=False).reset_index(drop=True)
