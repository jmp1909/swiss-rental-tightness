"""All SQL against the DuckDB warehouse, one function per chart/table need."""
import duckdb
import pandas as pd
import streamlit as st

from ingest.db import DB_PATH


@st.cache_resource
def get_conn() -> duckdb.DuckDBPyConnection:
    return duckdb.connect(str(DB_PATH), read_only=True)


@st.cache_data
def cantons() -> pd.DataFrame:
    return get_conn().execute(
        "SELECT kt_id, kt_abbr, kt_name_de, grossregion FROM dim_canton ORDER BY kt_name_de"
    ).df()


@st.cache_data
def vacancy_latest() -> pd.DataFrame:
    return get_conn().execute(
        """
        WITH latest AS (
            SELECT kt_id, max(year) AS year FROM fact_vacancy WHERE vacancy_rate_pct IS NOT NULL GROUP BY kt_id
        )
        SELECT c.kt_id, c.kt_abbr, c.kt_name_de, v.year, v.vacancy_rate_pct, v.vacant_count
        FROM latest l
        JOIN fact_vacancy v ON v.kt_id = l.kt_id AND v.year = l.year
        JOIN dim_canton c ON c.kt_id = l.kt_id
        """
    ).df()


@st.cache_data
def district_vacancy_latest_all() -> pd.DataFrame:
    """Latest vacancy rate per district, nationwide -- for the district-level map."""
    return get_conn().execute(
        """
        WITH latest AS (
            SELECT bezirk_id, max(year) AS year FROM fact_vacancy_district
            WHERE vacancy_rate_pct IS NOT NULL GROUP BY bezirk_id
        )
        SELECT d.bezirk_id, d.bezirk_name, c.kt_abbr, f.year, f.vacancy_rate_pct, f.vacant_count
        FROM latest l
        JOIN fact_vacancy_district f ON f.bezirk_id = l.bezirk_id AND f.year = l.year
        JOIN dim_district d ON d.bezirk_id = l.bezirk_id
        JOIN dim_canton c ON c.kt_id = d.kt_id
        """
    ).df()


@st.cache_data
def vacancy_trend(kt_ids: tuple[int, ...] | None = None) -> pd.DataFrame:
    where = "WHERE v.kt_id IN ({})".format(",".join(map(str, kt_ids))) if kt_ids else ""
    return get_conn().execute(
        f"""
        SELECT c.kt_abbr, c.kt_name_de, v.year, v.vacancy_rate_pct, v.vacant_count
        FROM fact_vacancy v JOIN dim_canton c ON c.kt_id = v.kt_id
        {where}
        ORDER BY c.kt_abbr, v.year
        """
    ).df()


@st.cache_data
def rent_latest(room_cat: str = "Totale") -> pd.DataFrame:
    return get_conn().execute(
        """
        WITH latest AS (
            SELECT kt_id, max(year) AS year FROM fact_rent WHERE room_count_cat = ? AND avg_rent_chf IS NOT NULL GROUP BY kt_id
        ),
        five_yr_ago AS (
            SELECT r.kt_id, r.avg_rent_chf AS rent_5y_ago
            FROM fact_rent r
            JOIN latest l ON l.kt_id = r.kt_id AND r.year = l.year - 5 AND r.room_count_cat = ?
        )
        SELECT c.kt_id, c.kt_abbr, c.kt_name_de, r.year, r.avg_rent_chf,
               f.rent_5y_ago,
               CASE WHEN f.rent_5y_ago > 0
                    THEN (r.avg_rent_chf - f.rent_5y_ago) * 100.0 / f.rent_5y_ago
                    ELSE NULL END AS rent_growth_5y_pct
        FROM latest l
        JOIN fact_rent r ON r.kt_id = l.kt_id AND r.year = l.year AND r.room_count_cat = ?
        JOIN dim_canton c ON c.kt_id = l.kt_id
        LEFT JOIN five_yr_ago f ON f.kt_id = l.kt_id
        """,
        [room_cat, room_cat, room_cat],
    ).df()


@st.cache_data
def rent_trend(kt_ids: tuple[int, ...] | None = None, room_cat: str = "Totale") -> pd.DataFrame:
    where = "AND r.kt_id IN ({})".format(",".join(map(str, kt_ids))) if kt_ids else ""
    return get_conn().execute(
        f"""
        SELECT c.kt_abbr, c.kt_name_de, r.year, r.avg_rent_chf
        FROM fact_rent r JOIN dim_canton c ON c.kt_id = r.kt_id
        WHERE r.room_count_cat = ? {where}
        ORDER BY c.kt_abbr, r.year
        """,
        [room_cat],
    ).df()


@st.cache_data
def population_latest() -> pd.DataFrame:
    return get_conn().execute(
        """
        WITH latest AS (
            SELECT kt_id, max(year) AS year FROM fact_population WHERE population_end IS NOT NULL GROUP BY kt_id
        ),
        five_yr_ago AS (
            SELECT p.kt_id, p.population_end AS population_5y_ago
            FROM fact_population p
            JOIN latest l ON l.kt_id = p.kt_id AND p.year = l.year - 5
        )
        SELECT c.kt_id, c.kt_abbr, c.kt_name_de, p.year, p.population_end,
               f.population_5y_ago,
               CASE WHEN f.population_5y_ago > 0
                    THEN (p.population_end - f.population_5y_ago) * 100.0 / f.population_5y_ago
                    ELSE NULL END AS pop_growth_5y_pct
        FROM latest l
        JOIN fact_population p ON p.kt_id = l.kt_id AND p.year = l.year
        JOIN dim_canton c ON c.kt_id = l.kt_id
        LEFT JOIN five_yr_ago f ON f.kt_id = l.kt_id
        """
    ).df()


@st.cache_data
def population_trend(kt_ids: tuple[int, ...] | None = None) -> pd.DataFrame:
    where = "WHERE p.kt_id IN ({})".format(",".join(map(str, kt_ids))) if kt_ids else ""
    return get_conn().execute(
        f"""
        SELECT c.kt_abbr, c.kt_name_de, p.year, p.population_end
        FROM fact_population p JOIN dim_canton c ON c.kt_id = p.kt_id
        {where}
        ORDER BY c.kt_abbr, p.year
        """
    ).df()


@st.cache_data
def migration_trend(kt_ids: tuple[int, ...] | None = None) -> pd.DataFrame:
    where = "WHERE m.kt_id IN ({})".format(",".join(map(str, kt_ids))) if kt_ids else ""
    return get_conn().execute(
        f"""
        SELECT c.kt_abbr, c.kt_name_de, m.year, m.immigration, m.emigration, m.net_migration
        FROM fact_migration m JOIN dim_canton c ON c.kt_id = m.kt_id
        {where}
        ORDER BY c.kt_abbr, m.year
        """
    ).df()


@st.cache_data
def canton_detail(kt_id: int) -> dict[str, pd.DataFrame]:
    con = get_conn()
    return {
        "vacancy": con.execute(
            "SELECT year, vacancy_rate_pct, vacant_count FROM fact_vacancy WHERE kt_id = ? ORDER BY year", [kt_id]
        ).df(),
        "rent": con.execute(
            "SELECT year, room_count_cat, avg_rent_chf FROM fact_rent WHERE kt_id = ? ORDER BY year", [kt_id]
        ).df(),
        "population": con.execute(
            "SELECT year, population_start, population_end FROM fact_population WHERE kt_id = ? ORDER BY year",
            [kt_id],
        ).df(),
        "migration": con.execute(
            "SELECT year, immigration, emigration, net_migration FROM fact_migration WHERE kt_id = ? ORDER BY year",
            [kt_id],
        ).df(),
        "new_dwellings": con.execute(
            "SELECT year, new_dwellings FROM fact_new_dwellings WHERE kt_id = ? ORDER BY year", [kt_id]
        ).df(),
    }


@st.cache_data
def new_dwellings_supply() -> pd.DataFrame:
    """New dwellings built in the trailing 5 years, per 1,000 residents --
    the supply-side counterpart to pop_growth_5y_pct. Uses each canton's own
    latest available new-dwellings year as the window end, and that same
    year's population as the denominator."""
    return get_conn().execute(
        """
        WITH latest AS (
            SELECT kt_id, max(year) AS year FROM fact_new_dwellings WHERE new_dwellings IS NOT NULL GROUP BY kt_id
        ),
        trailing_5y AS (
            SELECT d.kt_id, sum(d.new_dwellings) AS new_dwellings_5y
            FROM fact_new_dwellings d
            JOIN latest l ON l.kt_id = d.kt_id AND d.year BETWEEN l.year - 4 AND l.year
            GROUP BY d.kt_id
        ),
        pop AS (
            SELECT p.kt_id, p.year, p.population_end
            FROM fact_population p
            JOIN latest l ON l.kt_id = p.kt_id AND p.year = l.year
        )
        SELECT c.kt_id, c.kt_abbr, c.kt_name_de, l.year,
               t.new_dwellings_5y, pop.population_end,
               CASE WHEN pop.population_end > 0
                    THEN t.new_dwellings_5y * 1000.0 / pop.population_end
                    ELSE NULL END AS new_dwellings_per_1000_5y
        FROM latest l
        JOIN trailing_5y t ON t.kt_id = l.kt_id
        JOIN dim_canton c ON c.kt_id = l.kt_id
        LEFT JOIN pop ON pop.kt_id = l.kt_id
        """
    ).df()


@st.cache_data
def district_vacancy_latest(kt_id: int) -> pd.DataFrame:
    return get_conn().execute(
        """
        WITH latest AS (
            SELECT bezirk_id, max(year) AS year FROM fact_vacancy_district
            WHERE vacancy_rate_pct IS NOT NULL GROUP BY bezirk_id
        )
        SELECT d.bezirk_id, d.bezirk_name, f.year, f.vacancy_rate_pct, f.vacant_count
        FROM latest l
        JOIN fact_vacancy_district f ON f.bezirk_id = l.bezirk_id AND f.year = l.year
        JOIN dim_district d ON d.bezirk_id = l.bezirk_id
        WHERE d.kt_id = ?
        ORDER BY f.vacancy_rate_pct DESC
        """,
        [kt_id],
    ).df()


@st.cache_data
def districts() -> pd.DataFrame:
    """All districts with their parent canton, for the district picker --
    label disambiguates districts that share a name across cantons."""
    df = get_conn().execute(
        """
        SELECT d.bezirk_id, d.bezirk_name, d.kt_id, c.kt_abbr, c.kt_name_de
        FROM dim_district d JOIN dim_canton c ON c.kt_id = d.kt_id
        ORDER BY d.bezirk_name
        """
    ).df()
    df["label"] = df["bezirk_name"] + " (" + df["kt_abbr"] + ")"
    return df


@st.cache_data
def district_vacancy_trend(bezirk_id: str) -> pd.DataFrame:
    """A single district's own vacancy history -- this is real district-grain
    data (1995-2025), unlike the canton-context signals elsewhere."""
    return get_conn().execute(
        "SELECT year, vacancy_rate_pct, vacant_count FROM fact_vacancy_district WHERE bezirk_id = ? ORDER BY year",
        [bezirk_id],
    ).df()


@st.cache_data
def ingest_log() -> pd.DataFrame:
    return get_conn().execute(
        "SELECT source_name, resource_url, fetched_at, rows_loaded, status, detail FROM _ingest_log ORDER BY fetched_at DESC"
    ).df()
