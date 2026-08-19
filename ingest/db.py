"""DuckDB connection and schema management for the warehouse."""
from pathlib import Path

import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "warehouse.duckdb"
CANTONS_CSV = PROJECT_ROOT / "config" / "cantons.csv"
DISTRICTS_CSV = PROJECT_ROOT / "config" / "districts.csv"

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS dim_canton (
    kt_id       SMALLINT PRIMARY KEY,
    kt_abbr     VARCHAR UNIQUE,
    kt_name_de  VARCHAR,
    grossregion VARCHAR
);

CREATE TABLE IF NOT EXISTS fact_vacancy (
    kt_id            SMALLINT NOT NULL,
    year             SMALLINT NOT NULL,
    vacancy_rate_pct DOUBLE,
    vacant_count     INTEGER,
    source_dataset   VARCHAR,
    loaded_at        TIMESTAMP,
    PRIMARY KEY (kt_id, year)
);

CREATE TABLE IF NOT EXISTS dim_district (
    bezirk_id    VARCHAR PRIMARY KEY,
    bezirk_name  VARCHAR,
    kt_id        SMALLINT NOT NULL
);

CREATE TABLE IF NOT EXISTS fact_vacancy_district (
    bezirk_id        VARCHAR NOT NULL,
    year             SMALLINT NOT NULL,
    vacancy_rate_pct DOUBLE,
    vacant_count     INTEGER,
    source_dataset   VARCHAR,
    loaded_at        TIMESTAMP,
    PRIMARY KEY (bezirk_id, year)
);

CREATE TABLE IF NOT EXISTS fact_rent (
    kt_id           SMALLINT NOT NULL,
    year            SMALLINT NOT NULL,
    room_count_cat  VARCHAR NOT NULL,
    avg_rent_chf    DOUBLE,
    source_dataset  VARCHAR,
    loaded_at       TIMESTAMP,
    PRIMARY KEY (kt_id, year, room_count_cat)
);

CREATE TABLE IF NOT EXISTS fact_population (
    kt_id             SMALLINT NOT NULL,
    year              SMALLINT NOT NULL,
    population_start  INTEGER,
    population_end    INTEGER,
    source_dataset    VARCHAR,
    loaded_at         TIMESTAMP,
    PRIMARY KEY (kt_id, year)
);

CREATE TABLE IF NOT EXISTS fact_migration (
    kt_id           SMALLINT NOT NULL,
    year            SMALLINT NOT NULL,
    immigration     INTEGER,
    emigration      INTEGER,
    net_migration   INTEGER,
    source_dataset  VARCHAR,
    loaded_at       TIMESTAMP,
    PRIMARY KEY (kt_id, year)
);

CREATE TABLE IF NOT EXISTS fact_new_dwellings (
    kt_id              SMALLINT NOT NULL,
    year               SMALLINT NOT NULL,
    new_dwellings      INTEGER,
    source_dataset     VARCHAR,
    loaded_at          TIMESTAMP,
    PRIMARY KEY (kt_id, year)
);

CREATE TABLE IF NOT EXISTS fact_mietpreisindex_national (
    period          VARCHAR NOT NULL,
    index_value     DOUBLE,
    base_period     VARCHAR,
    source_dataset  VARCHAR,
    loaded_at       TIMESTAMP,
    PRIMARY KEY (period)
);

CREATE TABLE IF NOT EXISTS _ingest_log (
    source_name   VARCHAR,
    resource_url  VARCHAR,
    fetched_at    TIMESTAMP,
    rows_loaded   INTEGER,
    status        VARCHAR,
    detail        VARCHAR
);
"""


def get_connection(read_only: bool = False) -> duckdb.DuckDBPyConnection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return duckdb.connect(str(DB_PATH), read_only=read_only)


def init_schema(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(SCHEMA_DDL)
    seed_cantons(con)
    seed_districts(con)


def seed_cantons(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        INSERT INTO dim_canton
        SELECT kt_id, kt_abbr, kt_name_de, grossregion
        FROM read_csv_auto(?, header=True)
        WHERE kt_id NOT IN (SELECT kt_id FROM dim_canton)
        """,
        [str(CANTONS_CSV)],
    )


def seed_districts(con: duckdb.DuckDBPyConnection) -> None:
    con.execute(
        """
        INSERT INTO dim_district
        SELECT d.bezirk_id, d.bezirk_name, c.kt_id
        FROM read_csv_auto(?, header=True) d
        JOIN dim_canton c ON c.kt_abbr = d.kt_abbr
        WHERE d.bezirk_id NOT IN (SELECT bezirk_id FROM dim_district)
        """,
        [str(DISTRICTS_CSV)],
    )


def log_ingest(
    con: duckdb.DuckDBPyConnection,
    source_name: str,
    resource_url: str,
    rows_loaded: int,
    status: str,
    detail: str = "",
) -> None:
    con.execute(
        """
        INSERT INTO _ingest_log (source_name, resource_url, fetched_at, rows_loaded, status, detail)
        VALUES (?, ?, now(), ?, ?, ?)
        """,
        [source_name, resource_url, rows_loaded, status, detail],
    )


if __name__ == "__main__":
    conn = get_connection()
    init_schema(conn)
    print(conn.execute("SELECT count(*) FROM dim_canton").fetchone())
    conn.close()
