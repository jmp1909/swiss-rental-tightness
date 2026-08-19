"""Composite 'market tightness' heuristic: not a validated economic index,
just a transparent, adjustable combination of signals so geographies can be
ranked on one axis. Higher score = tighter (more landlord-favorable) market.

Four signals, each normalized then weighted:
  - vacancy (inverted): low vacancy = tight
  - demand-supply gap: population growth normalized minus new-dwellings-per-
    capita normalized. Population growth alone conflates demand pressure
    with tightness -- a fast-growing canton that's also building fast isn't
    necessarily tight. The gap nets out the supply response.
  - rent level: high rent can mean "tight" or just "affluent canton" --
    kept as a signal, not dropped, but its ambiguity is exactly why rent
    growth is offered alongside it rather than instead of it.
  - rent growth (5y): a cleaner tightness signal than level in principle,
    though it inherits any BFS methodology-break noise around 2015/2018.

score = sum(w_i * signal_i) / sum(w_i) -- weights don't need to sum to
anything in particular, and setting one to 0 drops that signal entirely.

Two normalization methods are supported (see `_normalize`): z-score
(standard, but sensitive to outliers with small N) and percentile rank
(robust to outliers, throws away magnitude). Selectable independently for
the canton and district scores since the "right" choice may differ with
sample size (26 cantons vs 143 districts).

Districts only have vacancy as a genuine district-grain signal -- BFS
doesn't publish rent, population, or construction data below canton level
(see DATA_AUDIT.md). The other three signals use each district's *parent
canton's* normalized value, shared by every district in that canton --
flagged explicitly via `_canton_context` column names, not hidden.
"""
import pandas as pd

from . import queries

NORMALIZATION_METHODS = ["zscore", "percentile"]


def _normalize(s: pd.Series, method: str) -> pd.Series:
    if method == "zscore":
        return (s - s.mean()) / s.std(ddof=0)
    elif method == "percentile":
        # rank in (0, 1], recentered to roughly [-1, 1] so it combines with
        # other signals on a comparable scale to z-score.
        return s.rank(pct=True) * 2 - 1
    raise ValueError(f"Unknown normalization method: {method!r}, expected one of {NORMALIZATION_METHODS}")


def _weighted_score(components: dict[str, tuple[pd.Series, float]]) -> pd.Series:
    total_weight = sum(w for _, w in components.values())
    if total_weight == 0:
        raise ValueError("At least one weight must be non-zero.")
    weighted_sum = sum(z * w for z, w in components.values())
    return weighted_sum / total_weight


def compute_tightness_index(
    w_vacancy: float = 1.0,
    w_demand_supply: float = 1.0,
    w_rent_level: float = 1.0,
    w_rent_growth: float = 1.0,
    method: str = "zscore",
) -> pd.DataFrame:
    vac = queries.vacancy_latest()[["kt_id", "kt_abbr", "kt_name_de", "vacancy_rate_pct"]]
    pop = queries.population_latest()[["kt_id", "pop_growth_5y_pct"]]
    supply = queries.new_dwellings_supply()[["kt_id", "new_dwellings_per_1000_5y"]]
    rent = queries.rent_latest()[["kt_id", "avg_rent_chf", "rent_growth_5y_pct"]]

    df = (
        vac
        .merge(pop, on="kt_id", how="left")
        .merge(supply, on="kt_id", how="left")
        .merge(rent, on="kt_id", how="left")
    )

    df["z_vacancy_inv"] = -_normalize(df["vacancy_rate_pct"], method)
    df["z_demand_supply_gap"] = (
        _normalize(df["pop_growth_5y_pct"], method) - _normalize(df["new_dwellings_per_1000_5y"], method)
    )
    df["z_rent_level"] = _normalize(df["avg_rent_chf"], method)
    df["z_rent_growth"] = _normalize(df["rent_growth_5y_pct"], method)

    df["tightness_score"] = _weighted_score({
        "vacancy": (df["z_vacancy_inv"], w_vacancy),
        "demand_supply": (df["z_demand_supply_gap"], w_demand_supply),
        "rent_level": (df["z_rent_level"], w_rent_level),
        "rent_growth": (df["z_rent_growth"], w_rent_growth),
    })

    return df.sort_values("tightness_score", ascending=False).reset_index(drop=True)


def compute_district_tightness_index(
    w_vacancy: float = 1.0,
    w_demand_supply: float = 1.0,
    w_rent_level: float = 1.0,
    w_rent_growth: float = 1.0,
    method: str = "zscore",
) -> pd.DataFrame:
    dist = queries.district_vacancy_latest_all()[["bezirk_id", "bezirk_name", "kt_abbr", "vacancy_rate_pct"]]

    # Canton-level normalization, computed once across the 26 cantons (the
    # correct reference population), then broadcast down to every district.
    canton_pop = queries.population_latest()[["kt_abbr", "pop_growth_5y_pct"]].copy()
    canton_supply = queries.new_dwellings_supply()[["kt_abbr", "new_dwellings_per_1000_5y"]].copy()
    canton_rent = queries.rent_latest()[["kt_abbr", "avg_rent_chf", "rent_growth_5y_pct"]].copy()

    canton_ctx = canton_pop.merge(canton_supply, on="kt_abbr", how="left").merge(canton_rent, on="kt_abbr", how="left")
    canton_ctx["z_demand_supply_gap_canton_context"] = (
        _normalize(canton_ctx["pop_growth_5y_pct"], method) - _normalize(canton_ctx["new_dwellings_per_1000_5y"], method)
    )
    canton_ctx["z_rent_level_canton_context"] = _normalize(canton_ctx["avg_rent_chf"], method)
    canton_ctx["z_rent_growth_canton_context"] = _normalize(canton_ctx["rent_growth_5y_pct"], method)

    df = dist.merge(
        canton_ctx[[
            "kt_abbr", "z_demand_supply_gap_canton_context",
            "z_rent_level_canton_context", "z_rent_growth_canton_context",
        ]],
        on="kt_abbr", how="left",
    )

    # District's own vacancy, normalized across all 143 districts -- the one
    # genuinely district-resolution signal in the score.
    df["z_vacancy_inv"] = -_normalize(df["vacancy_rate_pct"], method)

    df["tightness_score"] = _weighted_score({
        "vacancy": (df["z_vacancy_inv"], w_vacancy),
        "demand_supply": (df["z_demand_supply_gap_canton_context"], w_demand_supply),
        "rent_level": (df["z_rent_level_canton_context"], w_rent_level),
        "rent_growth": (df["z_rent_growth_canton_context"], w_rent_growth),
    })

    return df.sort_values("tightness_score", ascending=False).reset_index(drop=True)
