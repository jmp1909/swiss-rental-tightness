# Swiss Rental Market Tightness / Vacancy Risk Dashboard

A cantonal view of the Swiss rental market -- vacancy rate, rent levels, and population/migration
-- built entirely on official BFS (Federal Statistical Office) open data, pulled programmatically
into a normalized DuckDB warehouse and served through a Streamlit dashboard.

This was one of three candidate project ideas audited for real data availability before any code
was written (a cantonal mortgage/overheating tracker, this vacancy/tightness dashboard, and a
climate-risk exposure product). This idea won because every required series is confirmed
obtainable through a real bulk download or documented no-auth API at cantonal-or-finer
granularity -- the other two ideas each had a load-bearing series that isn't published at the
granularity they needed. Full audit: [`DATA_AUDIT.md`](DATA_AUDIT.md).

## Quick start

```bash
cd swiss-rental-tightness
python -m venv .venv
.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -e .
python -m ingest.run_all
streamlit run app/app.py
```

`data/warehouse.duckdb` is committed to the repo as a ready-to-use snapshot, so `streamlit run
app/app.py` alone is actually enough to see the dashboard -- the ingestion step above refreshes it
with whatever BFS has published since. That's it -- one venv, one ingestion command, one Streamlit
command to get current data. Re-running
`python -m ingest.run_all` is safe at any time (downloads are cached under `data/raw/`, and every
load is an upsert keyed on the fact table's primary key).

To run just one source: `python -m ingest.run_all --source vacancy_bfs`.

## What's in the warehouse

| Table | Grain | Source |
|---|---|---|
| `dim_canton` | 1 row per canton (26) | static seed, `config/cantons.csv` |
| `dim_district` | 1 row per district (155) | static seed, `config/districts.csv` |
| `fact_vacancy` | canton x year | BFS/stats.swiss SDMX, 1995-2025 |
| `fact_vacancy_district` | district x year | BFS/stats.swiss SDMX, 1995-2025 |
| `fact_rent` | canton x year x room-count | BFS Strukturerhebung, 2010-2024 |
| `fact_population` | canton x year | BFS PxWeb, 1971-2024 |
| `fact_migration` | canton x year | BFS PxWeb, 1971-2024 |
| `fact_mietpreisindex_national` | (unpopulated) | see limitations below |
| `_ingest_log` | 1 row per ingestion run per source | audit trail |

See [`DATA_AUDIT.md`](DATA_AUDIT.md) for exact source URLs, access methods, and licence terms.

## App pages

1. **Geographic Overview** -- choropleth map (canton or district toggle) + sortable table of the
   latest snapshot.
2. **Market Tightness Composite** -- a heuristic ranking (z-scored vacancy/growth/rent), explicitly
   labeled as a heuristic, not a validated economic index.
3. **Trends Over Time** -- per-canton time series, canton multiselect.
4. **Canton Detail** -- every metric for one selected canton, plus a district-level vacancy
   breakdown within it.
5. **Data Sources & Caveats** -- renders `DATA_AUDIT.md` in-app, plus the live ingestion log.

## Limitations (read before drawing conclusions)

- **Vacancy is loaded at canton and district level, not municipality.** District-level (155 units)
  was added as a first extension since it's the same cheap query and a stable geography. Full
  municipality-level (~2000 communes) is confirmed available in the same source, but Swiss
  municipalities merge often enough that using it properly needs a merger-aware
  `dim_municipality`, which is a distinct piece of modeling work, not just a bigger download. See
  `DATA_AUDIT.md` for the detail.
- **Rent figures are cross-sectional survey snapshots** (BFS Strukturerhebung), not a continuous
  monthly index. The app renders them as discrete markers per survey wave -- read year-to-year
  changes as step changes between waves, not a smooth trend. BFS also flags limited comparability
  across its 2015 and 2018 methodology changes.
- **The national rent index (Mietpreisindex/LIK) is not wired up** -- no bulk/API source for it
  could be confirmed within scope (see `DATA_AUDIT.md`). Even if it were, BFS publishes it at
  national level only, so it was never going to support cantonal comparison anyway.
- **Population/migration cover 1971-2024**; vacancy covers 1995-2025; rent covers 2010-2024 --
  the three series don't share a common start year, so any cross-series analysis implicitly uses
  each series' own available range.
- **The "market tightness" composite score is a heuristic built for this project**, not a
  peer-reviewed or industry-standard index. It's a transparent average of three z-scored signals,
  intended as a starting point for comparison, not a definitive ranking.
- **`dim_municipality` doesn't exist** -- adding true municipality-level vacancy (see above) would
  need a merger-aware version of it, which is out of scope for now.

## Project layout

```
swiss-rental-tightness/
  DATA_AUDIT.md              # source-by-source audit: URLs, access method, coverage, licence, gaps
  config/
    cantons.csv               # static canton dimension seed
    districts.csv              # static district (Bezirk) dimension seed, extracted from SDMX metadata
    cantons.geojson            # canton boundary geometry for the choropleth (BFS-derived, see DATA_AUDIT.md)
  ingest/
    db.py                      # DuckDB schema + connection helper
    http.py                    # cached fetch helpers (GET and POST)
    run_all.py                 # orchestrates all sources, idempotent
    sources/                   # one module per data source
  app/
    app.py                     # Streamlit entry point
    pages/                     # the 5 dashboard pages
    lib/                       # SQL queries, scoring, chart builders
  tests/
    test_schema.py             # row-count, PK-uniqueness, FK-integrity checks against real data
```

## Deploying (free, for others to access)

This is set up to deploy on [Streamlit Community Cloud](https://share.streamlit.io) at no cost:

1. Push this repo to a **public** GitHub repo (Community Cloud's free tier requires public repos).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in with GitHub, click "New app".
3. Point it at this repo, branch `main`, main file path `app/app.py`. It reads `requirements.txt`
   and `.python-version` automatically -- no other config needed.
4. Deploy. The committed `data/warehouse.duckdb` snapshot means the app works immediately, with no
   dependency on BFS's servers being reachable at boot time.

To refresh the live app with newer data: run `python -m ingest.run_all` locally, commit the
updated `data/warehouse.duckdb`, and push -- Community Cloud redeploys automatically on push.
Free-tier apps also go to sleep after a period with no visitors and wake back up (cold start of a
few seconds) on the next visit -- normal behavior, not a bug.

## Tests

```bash
pip install -e ".[dev]"    # adds pytest on top of the base install
python -m ingest.run_all   # populate the warehouse first
python -m pytest tests/
```

Tests assert against the real ingested warehouse (all 26 cantons present, no orphaned foreign
keys, plausible value ranges) -- there are no mocked fixtures, since the point of this project is
that the numbers are genuinely pulled from live BFS sources.
