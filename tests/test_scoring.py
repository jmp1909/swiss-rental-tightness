"""Tests for the tightness-score heuristic (app/lib/scoring.py) against the
real ingested warehouse -- same philosophy as test_schema.py, no mocks.
"""
import pytest

from app.lib import scoring


@pytest.mark.parametrize("method", scoring.NORMALIZATION_METHODS)
def test_canton_score_covers_all_26(method):
    df = scoring.compute_tightness_index(method=method)
    assert len(df) == 26
    assert df["kt_abbr"].nunique() == 26


@pytest.mark.parametrize("method", scoring.NORMALIZATION_METHODS)
def test_canton_score_sorted_descending(method):
    df = scoring.compute_tightness_index(method=method)
    assert list(df["tightness_score"]) == sorted(df["tightness_score"], reverse=True)


@pytest.mark.parametrize("method", scoring.NORMALIZATION_METHODS)
def test_canton_score_weight_zero_drops_signal(method):
    # With everything but vacancy weighted to 0, the ranking must exactly
    # match ranking by vacancy alone (inverted).
    df = scoring.compute_tightness_index(
        w_vacancy=1.0, w_demand_supply=0.0, w_rent_level=0.0, w_rent_growth=0.0, method=method,
    )
    expected_order = df.sort_values("vacancy_rate_pct")["kt_abbr"].tolist()
    assert df["kt_abbr"].tolist() == expected_order


def test_canton_score_requires_nonzero_weight():
    with pytest.raises(ValueError):
        scoring.compute_tightness_index(0.0, 0.0, 0.0, 0.0)


def test_canton_score_weight_scale_invariant():
    # (1,1,1,1) and (2,2,2,2) must produce identical scores -- weights are
    # normalized by their own sum, only relative size matters.
    a = scoring.compute_tightness_index(1.0, 1.0, 1.0, 1.0).set_index("kt_abbr")["tightness_score"]
    b = scoring.compute_tightness_index(2.0, 2.0, 2.0, 2.0).set_index("kt_abbr")["tightness_score"]
    assert a.sub(b).abs().max() < 1e-9


def test_canton_score_unknown_method_rejected():
    with pytest.raises(ValueError):
        scoring.compute_tightness_index(method="not-a-real-method")


@pytest.mark.parametrize("method", scoring.NORMALIZATION_METHODS)
def test_district_score_covers_all_143(method):
    df = scoring.compute_district_tightness_index(method=method)
    assert len(df) == 143
    assert df["bezirk_id"].nunique() == 143


@pytest.mark.parametrize("method", scoring.NORMALIZATION_METHODS)
def test_district_score_sorted_descending(method):
    df = scoring.compute_district_tightness_index(method=method)
    assert list(df["tightness_score"]) == sorted(df["tightness_score"], reverse=True)


@pytest.mark.parametrize("method", scoring.NORMALIZATION_METHODS)
def test_district_score_vacancy_only_matches_own_vacancy_ranking(method):
    df = scoring.compute_district_tightness_index(
        w_vacancy=1.0, w_demand_supply=0.0, w_rent_level=0.0, w_rent_growth=0.0, method=method,
    )
    expected_order = df.sort_values("vacancy_rate_pct")["bezirk_id"].tolist()
    assert df["bezirk_id"].tolist() == expected_order


def test_district_score_context_columns_constant_within_canton():
    # Every district in the same canton must share the same borrowed
    # canton-context values (that's the whole point of "context", not a
    # genuine per-district signal).
    df = scoring.compute_district_tightness_index()
    context_cols = [
        "z_demand_supply_gap_canton_context",
        "z_rent_level_canton_context",
        "z_rent_growth_canton_context",
    ]
    per_canton_unique = df.groupby("kt_abbr")[context_cols].nunique()
    assert (per_canton_unique <= 1).all().all()


def test_zscore_and_percentile_agree_on_top_and_bottom_canton():
    # Different normalization shouldn't flip who's tightest/loosest for
    # such a clear-cut case (Zug consistently tightest in prior manual runs).
    z = scoring.compute_tightness_index(method="zscore")
    p = scoring.compute_tightness_index(method="percentile")
    assert z.iloc[0]["kt_abbr"] == p.iloc[0]["kt_abbr"]
    assert z.iloc[-1]["kt_abbr"] == p.iloc[-1]["kt_abbr"]
