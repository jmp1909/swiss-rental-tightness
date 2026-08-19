"""Schema-level sanity checks against the ingested warehouse.

Run `python -m ingest.run_all` before this test suite -- it asserts on real
ingested data, not fixtures, since the whole point of the project is that
the data is genuinely pulled from live BFS sources.
"""
import pytest

from ingest.db import get_connection

FACT_TABLES_WITH_CANTON = [
    "fact_vacancy",
    "fact_rent",
    "fact_population",
    "fact_migration",
    "fact_new_dwellings",
]


@pytest.fixture(scope="module")
def con():
    connection = get_connection(read_only=True)
    yield connection
    connection.close()


def test_all_26_cantons_present(con):
    n = con.execute("SELECT count(*) FROM dim_canton").fetchone()[0]
    assert n == 26


def test_all_155_districts_present(con):
    n = con.execute("SELECT count(*) FROM dim_district").fetchone()[0]
    assert n == 155


def test_dim_district_no_orphaned_kt_id(con):
    n = con.execute(
        """
        SELECT count(*) FROM dim_district d
        LEFT JOIN dim_canton c ON d.kt_id = c.kt_id
        WHERE c.kt_id IS NULL
        """
    ).fetchone()[0]
    assert n == 0


def test_fact_vacancy_district_has_rows(con):
    n = con.execute("SELECT count(*) FROM fact_vacancy_district").fetchone()[0]
    assert n > 0


def test_fact_vacancy_district_no_orphaned_bezirk_id(con):
    n = con.execute(
        """
        SELECT count(*) FROM fact_vacancy_district f
        LEFT JOIN dim_district d ON f.bezirk_id = d.bezirk_id
        WHERE d.bezirk_id IS NULL
        """
    ).fetchone()[0]
    assert n == 0


def test_fact_vacancy_district_rate_in_plausible_range(con):
    row = con.execute(
        "SELECT min(vacancy_rate_pct), max(vacancy_rate_pct) FROM fact_vacancy_district WHERE vacancy_rate_pct IS NOT NULL"
    ).fetchone()
    lo, hi = row
    assert 0 <= lo
    assert hi < 20


def test_dim_canton_abbr_unique(con):
    n_total = con.execute("SELECT count(*) FROM dim_canton").fetchone()[0]
    n_distinct = con.execute("SELECT count(DISTINCT kt_abbr) FROM dim_canton").fetchone()[0]
    assert n_total == n_distinct


@pytest.mark.parametrize("table", FACT_TABLES_WITH_CANTON)
def test_fact_table_has_rows(con, table):
    n = con.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
    assert n > 0, f"{table} is empty -- did ingestion run?"


@pytest.mark.parametrize("table", FACT_TABLES_WITH_CANTON)
def test_fact_table_covers_all_cantons(con, table):
    n = con.execute(f"SELECT count(DISTINCT kt_id) FROM {table}").fetchone()[0]
    assert n == 26, f"{table} only covers {n}/26 cantons"


@pytest.mark.parametrize("table", FACT_TABLES_WITH_CANTON)
def test_fact_table_no_orphaned_kt_id(con, table):
    n = con.execute(
        f"""
        SELECT count(*) FROM {table} f
        LEFT JOIN dim_canton c ON f.kt_id = c.kt_id
        WHERE c.kt_id IS NULL
        """
    ).fetchone()[0]
    assert n == 0


def test_fact_vacancy_rate_in_plausible_range(con):
    row = con.execute(
        "SELECT min(vacancy_rate_pct), max(vacancy_rate_pct) FROM fact_vacancy WHERE vacancy_rate_pct IS NOT NULL"
    ).fetchone()
    lo, hi = row
    assert 0 <= lo, "negative vacancy rate found"
    assert hi < 15, f"implausibly high vacancy rate found: {hi}"


def test_fact_population_end_exceeds_start_generally(con):
    # Switzerland's population has grown almost every year since 1971;
    # a large majority of (canton, year) rows should show growth.
    row = con.execute(
        """
        SELECT
            sum(CASE WHEN population_end >= population_start THEN 1 ELSE 0 END) AS growing,
            count(*) AS total
        FROM fact_population
        WHERE population_start IS NOT NULL AND population_end IS NOT NULL
        """
    ).fetchone()
    growing, total = row
    assert growing / total > 0.8


def test_ingest_log_has_entries(con):
    n = con.execute("SELECT count(*) FROM _ingest_log").fetchone()[0]
    assert n > 0
