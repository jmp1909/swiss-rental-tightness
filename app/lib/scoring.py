"""Composite 'market tightness' heuristic: not a validated economic index,
just a transparent combination of three signals so cantons can be ranked
on one axis. Higher score = tighter (more landlord-favorable) market.

score = z(-vacancy_rate) + z(pop_growth_5y_pct) + z(avg_rent_chf)

Each input is z-scored across cantons for the latest available year of that
series (years don't line up exactly across sources -- see Data Sources page).
"""
import pandas as pd

from . import queries


def compute_tightness_index() -> pd.DataFrame:
    vac = queries.vacancy_latest()[["kt_id", "kt_abbr", "kt_name_de", "vacancy_rate_pct"]]
    pop = queries.population_latest()[["kt_id", "pop_growth_5y_pct"]]
    rent = queries.rent_latest()[["kt_id", "avg_rent_chf"]]

    df = vac.merge(pop, on="kt_id", how="left").merge(rent, on="kt_id", how="left")

    def zscore(s: pd.Series) -> pd.Series:
        return (s - s.mean()) / s.std(ddof=0)

    df["z_vacancy_inv"] = -zscore(df["vacancy_rate_pct"])
    df["z_pop_growth"] = zscore(df["pop_growth_5y_pct"])
    df["z_rent"] = zscore(df["avg_rent_chf"])
    df["tightness_score"] = df[["z_vacancy_inv", "z_pop_growth", "z_rent"]].mean(axis=1)

    return df.sort_values("tightness_score", ascending=False).reset_index(drop=True)
