"""Ingest cantonal vacancy rate (Leerwohnungsziffer) from BFS's SDMX platform
(stats.swiss), dataflow CH1.LWZ/DF_LWZ_1, confirmed in the Phase 0 spike as a
live, no-auth, bulk CSV endpoint replacing the old PxWeb cube for this topic.

Filtered to canton-level rows only (GR_KT_GDE = the 26 canton abbreviations)
-- the unfiltered dataflow includes every Grossregion/Kanton/Bezirk/Gemeinde
combination (~7M rows, ~750MB) which is impractical to pull on every run.
WOHN_ANZAHL (room count) and LEERWOHN_TYP (vacancy type) are filtered to
their "_T" (total) code. MEASURE_DIMENSION V = absolute vacant dwelling
count, PC = vacancy rate percent. FREQ = A (annual, reference date June 1).
"""
import csv as csv_module
from datetime import datetime, timezone

from ..db import CANTONS_CSV, get_connection, init_schema, log_ingest
from ..http import fetch

SOURCE = "vacancy_bfs"
BASE_URL = "https://disseminate.stats.swiss/rest/data/CH1.LWZ,DF_LWZ_1,1.0.0"
HEADERS = {"Accept": "application/vnd.sdmx.data+csv;version=1.0.0"}


def _canton_abbrs() -> list[str]:
    with open(CANTONS_CSV, encoding="utf-8") as f:
        return [row["kt_abbr"] for row in csv_module.DictReader(f)]


def _build_url() -> str:
    canton_key = "+".join(_canton_abbrs())
    key = f"{canton_key}._T._T.V+PC.A"
    return f"{BASE_URL}/{key}"


def run() -> int:
    url = _build_url()
    path = fetch(url, SOURCE, filename="vacancy_cantons.csv", headers=HEADERS)

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

    abbr_to_id = {}
    with open(CANTONS_CSV, encoding="utf-8") as f:
        for row in csv_module.DictReader(f):
            abbr_to_id[row["kt_abbr"]] = int(row["kt_id"])

    rows_to_load = []
    for (kt_abbr, year), vals in by_key.items():
        kt_id = abbr_to_id.get(kt_abbr)
        if kt_id is None:
            continue
        rows_to_load.append((
            kt_id, year,
            vals.get("vacancy_rate_pct"),
            vals.get("vacant_count"),
            SOURCE, datetime.now(timezone.utc),
        ))

    con = get_connection()
    init_schema(con)
    con.executemany(
        """
        INSERT INTO fact_vacancy (kt_id, year, vacancy_rate_pct, vacant_count, source_dataset, loaded_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (kt_id, year) DO UPDATE SET
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
    print(f"Loaded {n} fact_vacancy rows")
