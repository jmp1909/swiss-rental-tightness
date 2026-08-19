"""Ingest cantonal migration components from BFS PxWeb cube px-x-0102020000_101
("Demografische Bilanz nach Kanton"). Components: Einwanderung inkl. Änderung
des Bevölkerungstyps (code 4, treated as immigration), Auswanderung (code 6,
emigration), Wanderungssaldo inkl. Änderung des Bevölkerungstyps (code 8, net
migration). Same Kanton/nationality/sex scope as population_bfs.py.
"""
from datetime import datetime, timezone

import pandas as pd

from ..db import get_connection, init_schema, log_ingest
from ..http import post_json_cached
from .population_bfs import KANTON_CODES, _canton_abbr_to_id

SOURCE = "migration_bfs"
CUBE_URL = "https://www.pxweb.bfs.admin.ch/api/v1/de/px-x-0102020000_101/px-x-0102020000_101.px"

QUERY = {
    "query": [
        {"code": "Kanton", "selection": {"filter": "item", "values": KANTON_CODES}},
        {"code": "Staatsangehörigkeit (Kategorie)", "selection": {"filter": "item", "values": ["0"]}},
        {"code": "Geschlecht", "selection": {"filter": "item", "values": ["0"]}},
        {"code": "Demografische Komponente", "selection": {"filter": "item", "values": ["4", "6", "8"]}},
    ],
    "response": {"format": "csv"},
}


def run() -> int:
    path = post_json_cached(CUBE_URL, QUERY, SOURCE, "demografische_bilanz_migration.csv")
    df = pd.read_csv(path, encoding="cp1252")
    df.columns = [c.strip() for c in df.columns]

    kt_lookup = _canton_abbr_to_id()

    rows_to_load = []
    for _, row in df.iterrows():
        kt_id = kt_lookup.get(row["Kanton"])
        if kt_id is None:
            continue
        year = int(row["Jahr"])
        immigration = row.get("Einwanderung inkl. Änderung des Bevölkerungstyps")
        emigration = row.get("Auswanderung")
        net_migration = row.get("Wanderungssaldo inkl. Änderung des Bevölkerungstyps")
        rows_to_load.append((
            kt_id, year,
            None if pd.isna(immigration) else int(immigration),
            None if pd.isna(emigration) else int(emigration),
            None if pd.isna(net_migration) else int(net_migration),
            SOURCE, datetime.now(timezone.utc),
        ))

    con = get_connection()
    init_schema(con)
    con.executemany(
        """
        INSERT INTO fact_migration (kt_id, year, immigration, emigration, net_migration, source_dataset, loaded_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT (kt_id, year) DO UPDATE SET
            immigration = excluded.immigration,
            emigration = excluded.emigration,
            net_migration = excluded.net_migration,
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
    print(f"Loaded {n} fact_migration rows")
