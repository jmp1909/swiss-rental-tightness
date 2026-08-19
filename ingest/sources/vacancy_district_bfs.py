"""Ingest district-level (Bezirk) vacancy rate from the same BFS/stats.swiss
SDMX source as vacancy_bfs.py, one geography level finer than canton.

District codes (e.g. "B_101") were extracted once from the dataflow's own
SDMX structure metadata (every code in the GR_KT_GDE codelist whose Parent
is a canton abbreviation) into config/districts.csv -- see that file's
generation note in DATA_AUDIT.md. There are 155 districts; some cantons
without an administrative district layer (e.g. Appenzell Innerrhoden,
Geneva) have a single pseudo-district standing in for the whole canton.

Same total/total/V+PC/annual filter as vacancy_bfs.py -- this is the same
already-cheap query (the full "all geography levels" pull is ~16MB / ~142k
rows total, not the ~750MB the fully unfiltered dataflow would be), just
keyed to district codes instead of canton codes.
"""
import csv as csv_module
from datetime import datetime, timezone

from ..db import DISTRICTS_CSV, get_connection, init_schema, log_ingest
from ..http import fetch

SOURCE = "vacancy_district_bfs"
BASE_URL = "https://disseminate.stats.swiss/rest/data/CH1.LWZ,DF_LWZ_1,1.0.0"
HEADERS = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}


def _district_ids() -> list[str]:
    with open(DISTRICTS_CSV, encoding="utf-8") as f:
        return [row["bezirk_id"] for row in csv_module.DictReader(f)]


def _build_url() -> str:
    district_key = "+".join(_district_ids())
    key = f"{district_key}._T._T.V+PC.A"
    return f"{BASE_URL}/{key}"


def run() -> int:
    url = _build_url()
    path = fetch(url, SOURCE, filename="vacancy_districts.csv", headers=HEADERS)

    with open(path, encoding="utf-8") as f:
        reader = csv_module.DictReader(f)
        by_key: dict[tuple[str, int], dict] = {}
        for row in reader:
            if row["OBS_VALUE"] == "":
                continue
            key = (row["GR_KT_GDE"], int(row["TIME_PERIOD"]))
            entry = by_key.setdefault(key, {})
            if row["MEASURE_DIMENSION"] == "V":
                entry["vacant_count"] = int(float(row["OBS_VALUE"]))
            elif row["MEASURE_DIMENSION"] == "PC":
                entry["vacancy_rate_pct"] = float(row["OBS_VALUE"])

    valid_ids = set(_district_ids())
    rows_to_load = []
    for (bezirk_id, year), vals in by_key.items():
        if bezirk_id not in valid_ids:
            continue
        rows_to_load.append((
            bezirk_id, year,
            vals.get("vacancy_rate_pct"),
            vals.get("vacant_count"),
            SOURCE, datetime.now(timezone.utc),
        ))

    con = get_connection()
    init_schema(con)
    con.executemany(
        """
        INSERT INTO fact_vacancy_district (bezirk_id, year, vacancy_rate_pct, vacant_count, source_dataset, loaded_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (bezirk_id, year) DO UPDATE SET
            vacancy_rate_pct = excluded.vacancy_rate_pct,
            vacant_count = excluded.vacant_count,
            source_dataset = excluded.source_dataset,
            loaded_at = excluded.loaded_at
        """,
        rows_to_load,
    )
    log_ingest(con, SOURCE, url, len(rows_to_load), "ok")
    con.close()
    return len(rows_to_load)


if __name__ == "__main__":
    n = run()
    print(f"Loaded {n} fact_vacancy_district rows")
