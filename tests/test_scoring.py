"""Tests for the tightness-score heuristic (app/lib/scoring.py) against the
real ingested warehouse -- same philosophy as test_schema.py, no mocks.
"""
import pytest

from app.lib import scoring


def test_canton_score_covers_all_26():
    df = scoring.compute_tightness_index()
    assert len(df) == 26
    assert df["kt_abbr"].nunique() == 26


def test_canton_score_sorted_descending():
    df = scoring.compute_tightness_index()
    assert list(df["tightness_score"]) == sorted(df["tightness_score"], reverse=True)


def test_canton_score_weight_zero_drops_signal():
    # With rent and pop_growth weighted to 0, the ranking must exactly match
    # ranking by vacancy alone (inverted).
    df = scoring.compute_tightness_index(w_vacancy=1.0, w_pop_growth=0.0, w_rent=0.0)
    expected_order = df.sort_values("vacancy_rate_pct")["kt_abbr"].tolist()
    assert df["kt_abbr"].tolist() == expected_order


def test_canton_score_requires_nonzero_weight():
    with pytest.raises(ValueError):
        scoring.compute_tightness_index(0.0, 0.0, 0.0)


def test_canton_score_weight_scale_invariant():
    # (1,1,1) and (2,2,2) must produce identical scores -- weights are
    # normalized by their own sum, only relative size matters.
    a = scoring.compute_tightness_index(1.0, 1.0, 1.0).set_index("kt_abbr")["tightness_score"]
    b = scoring.compute_tightness_index(2.0, 2.0, 2.0).set_index("kt_abbr")["tightness_score"]
    assert a.sub(b).abs().max() < 1e-9


def test_district_score_covers_all_143():
    df = scoring.compute_district_tightness_index()
    assert len(df) == 143
    assert df["bezirk_id"].nunique() == 143


def test_district_score_sorted_descending():
    df = scoring.compute_district_tightness_index()
    assert list(df["tightness_score"]) == sorted(df["tightness_score"], reverse=True)


def test_district_score_vacancy_only_matches_own_vacancy_ranking():
    df = scoring.compute_district_tightness_index(w_vacancy=1.0, w_pop_growth=0.0, w_rent=0.0)
    expected_order = df.sort_values("vacancy_rate_pct")["bezirk_id"].tolist()
    assert df["bezirk_id"].tolist() == expected_order


def test_district_score_context_columns_constant_within_canton():
    # Every district in the same canton must share the same borrowed
    # canton-context z-scores (that's the whole point of "context", not a
    # genuine per-district signal).
    df = scoring.compute_district_tightness_index()
    per_canton_unique = df.groupby("kt_abbr")[["z_pop_growth_canton_context", "z_rent_canton_context"]].nunique()
    assert (per_canton_unique <= 1).all().all()
