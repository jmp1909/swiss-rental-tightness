"""Orchestrates all ingestion sources. Idempotent: safe to re-run.

Usage:
    python -m ingest.run_all              # run all sources
    python -m ingest.run_all --source rent_bfs   # run just one
"""
import argparse
import sys

from .db import get_connection, init_schema
from .sources import (
    mietpreisindex_bfs,
    migration_bfs,
    new_dwellings_bfs,
    population_bfs,
    rent_bfs,
    vacancy_bfs,
    vacancy_district_bfs,
)

SOURCES = {
    "rent_bfs": rent_bfs,
    "population_bfs": population_bfs,
    "migration_bfs": migration_bfs,
    "new_dwellings_bfs": new_dwellings_bfs,
    "vacancy_bfs": vacancy_bfs,
    "vacancy_district_bfs": vacancy_district_bfs,
    "mietpreisindex_bfs": mietpreisindex_bfs,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", choices=SOURCES.keys(), default=None)
    args = parser.parse_args()

    con = get_connection()
    init_schema(con)
    con.close()

    targets = [args.source] if args.source else list(SOURCES.keys())
    for name in targets:
        module = SOURCES[name]
        print(f"=== {name} ===")
        try:
            n = module.run()
            print(f"    {n} rows loaded")
        except Exception as exc:
            print(f"    FAILED: {exc}", file=sys.stderr)
            raise


if __name__ == "__main__":
    main()
