"""Ingest cantonal population stock from BFS PxWeb cube px-x-0102020000_101
("Demografische Bilanz nach Kanton"). Components used: Bestand am 1. Januar
(code 0) and Bestand am 31. Dezember (code 14), Kanton codes 1-26 (BFS
official numbering, excludes 0=Schweiz total and 27=Ohne Angabe), all years
available (1971-present), total nationality/sex only (codes 0/0).
"""
from datetime import datetime, timezone

import pandas as pd

from ..db import get_connection, init_schema, log_ingest
from ..http import post_json_cached

SOURCE = "population_bfs"
CUBE_URL = "https://www.pxweb.bfs.admin.ch/api/v1/de/px-x-0102020000_101/px-x-0102020000_101.px"
KANTON_CODES = [str(i) for i in range(1, 27)]

QUERY = {
    "query": [
        {"code": "Kanton", "selection": {"filter": "item", "values": KANTON_CODES}},
        {"code": "Staatsangehörigkeit (Kategorie)", "selection": {"filter": "item", "values": ["0"]}},
        {"code": "Geschlecht", "selection": {"filter": "item", "values": ["0"]}},
        {"code": "Demografische Komponente", "selection": {"filter": "item", "values": ["0", "14"]}},
    ],
    "response": {"format": "csv"},
}


def run() -> int:
    path = post_json_cached(CUBE_URL, QUERY, SOURCE, "demografische_bilanz_population.csv")
    df = pd.read_csv(path, encoding="cp1252")
    df.columns = [c.strip() for c in df.columns]

    kt_lookup = _canton_abbr_to_id()

    rows_to_load = []
    for _, row in df.iterrows():
        kt_abbr = row["Kanton"]
        kt_id = kt_lookup.get(kt_abbr)
        if kt_id is None:
            continue
        year = int(row["Jahr"])
        pop_start = row.get("Bestand am 1. Januar")
        pop_end = row.get("Bestand am 31. Dezember")
        rows_to_load.append((
            kt_id, year,
            None if pd.isna(pop_start) else int(pop_start),
            None if pd.isna(pop_end) else int(pop_end),
            SOURCE, datetime.now(timezone.utc),
        ))

    con = get_connection()
    init_schema(con)
    con.executemany(
        """
        INSERT INTO fact_population (kt_id, year, population_start, population_end, source_dataset, loaded_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT (kt_id, year) DO UPDATE SET
            population_start = excluded.population_start,
            population_end = excluded.population_end,
            source_dataset = excluded.source_dataset,
            loaded_at = excluded.loaded_at
        """,
        rows_to_load,
    )
    log_ingest(con, SOURCE, CUBE_URL, len(rows_to_load), "ok")
    con.close()
    return len(rows_to_load)


def _canton_abbr_to_id() -> dict:
    """Map full German canton names (as returned by PxWeb) to kt_id via cantons.csv,
    matching on a normalized long-name basis since PxWeb uses e.g. 'Zürich',
    'Bern / Berne', 'Graubünden / Grigioni / Grischun'."""
    import csv
    from ..db import CANTONS_CSV

    long_names = {
        "Zürich": "ZH", "Bern / Berne": "BE", "Luzern": "LU", "Uri": "UR",
        "Schwyz": "SZ", "Obwalden": "OW", "Nidwalden": "NW", "Glarus": "GL",
        "Zug": "ZG", "Fribourg / Freiburg": "FR", "Solothurn": "SO",
        "Basel-Stadt": "BS", "Basel-Landschaft": "BL", "Schaffhausen": "SH",
        "Appenzell Ausserrhoden": "AR", "Appenzell Innerrhoden": "AI",
        "St. Gallen": "SG", "Graubünden / Grigioni / Grischun": "GR",
        "Aargau": "AG", "Thurgau": "TG", "Ticino": "TI", "Vaud": "VD",
        "Valais / Wallis": "VS", "Neuchâtel": "NE", "Genève": "GE", "Jura": "JU",
    }
    abbr_to_id = {}
    with open(CANTONS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            abbr_to_id[row["kt_abbr"]] = int(row["kt_id"])
    return {name: abbr_to_id[abbr] for name, abbr in long_names.items()}


if __name__ == "__main__":
    n = run()
    print(f"Loaded {n} fact_population rows")
