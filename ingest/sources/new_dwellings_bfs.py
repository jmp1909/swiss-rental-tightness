"""Ingest newly constructed dwellings by canton and year -- the supply-side
counterpart to population growth in the tightness score.

Source: BFS STAT-TAB PxWeb cube px-x-0904030000_105, "Neu erstellte
Wohnungen nach Grossregion / Kanton / Gemeinde und Anzahl Zimmer, ab 2013".
Confirmed live via the same PxWeb API used for population/migration.

Note this is construction *flow* (dwellings completed that year), not a
total dwelling *stock* level -- a clean bulk time series for total stock by
canton wasn't found within scope (BFS's Gebäude- und Wohnungsstatistik
publishes stock as an annual full-address geodata snapshot, not a
canton-level time series cube). Flow is used as a construction-intensity
proxy instead: summed over 5 years and expressed per 1,000 residents in
scoring.py, comparable across cantons of different sizes.

Canton codes in this cube (e.g. "8" = Kanton Zürich) are cube-specific
sequential IDs, but conveniently appear in the same 1-26 official BFS
canton order as everywhere else in this project, confirmed by inspecting
the codelist -- so they're just zipped against kt_id 1..26 directly rather
than needing a name-matching step.
"""
from datetime import datetime, timezone

import pandas as pd

from ..db import get_connection, init_schema, log_ingest
from ..http import post_json_cached

SOURCE = "new_dwellings_bfs"
CUBE_URL = "https://www.pxweb.bfs.admin.ch/api/v1/de/px-x-0904030000_105/px-x-0904030000_105.px"

# Cube-specific canton codes, in official BFS canton order (kt_id 1-26).
CANTON_CUBE_CODES = [
    "8", "169", "505", "586", "606", "637", "645", "657", "661", "673",
    "800", "907", "911", "998", "1025", "1046", "1052", "1128", "1230",
    "1428", "1509", "1616", "1917", "2040", "2068", "2114",
]
GEO_VAR = "Grossregion (<<) / Kanton (-) / Gemeinde (......)"
YEARS = [str(i) for i in range(12)]  # codes 0-11 -> years 2013-2024

QUERY = {
    "query": [
        {"code": GEO_VAR, "selection": {"filter": "item", "values": CANTON_CUBE_CODES}},
        {"code": "Anzahl Zimmer", "selection": {"filter": "item", "values": ["0"]}},  # Total
        {"code": "Jahr", "selection": {"filter": "item", "values": YEARS}},
    ],
    "response": {"format": "csv"},
}


def run() -> int:
    path = post_json_cached(CUBE_URL, QUERY, SOURCE, "new_dwellings_canton.csv")
    df = pd.read_csv(path, encoding="cp1252")
    df.columns = [c.strip() for c in df.columns]

    year_cols = [c for c in df.columns if c.isdigit()]
    canton_rows = df[df[GEO_VAR].str.startswith("- ")].reset_index(drop=True)
    assert len(canton_rows) == len(CANTON_CUBE_CODES), (
        f"Expected {len(CANTON_CUBE_CODES)} canton rows, got {len(canton_rows)} -- "
        "cube layout may have changed, positional kt_id mapping is no longer safe."
    )

    rows_to_load = []
    for kt_id in range(1, len(canton_rows) + 1):
        row = canton_rows.iloc[kt_id - 1]
        for year_col in year_cols:
            value = row[year_col]
            rows_to_load.append((
                kt_id, int(year_col),
                None if pd.isna(value) else int(value),
                SOURCE, datetime.now(timezone.utc),
            ))

    con = get_connection()
    init_schema(con)
    con.executemany(
        """
        INSERT INTO fact_new_dwellings (kt_id, year, new_dwellings, source_dataset, loaded_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT (kt_id, year) DO UPDATE SET
            new_dwellings = excluded.new_dwellings,
            source_dataset = excluded.source_dataset,
            loaded_at = excluded.loaded_at
        """,
        rows_to_load,
    )
    log_ingest(con, SOURCE, CUBE_URL, len(rows_to_load), "ok")
    con.close()
    return len(rows_to_load)


if __name__ == "__main__":
    n = run()
    print(f"Loaded {n} fact_new_dwellings rows")
