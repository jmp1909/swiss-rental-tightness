# Data Audit

This document records exactly what data this project draws on, where it comes from, and what its
limits are. It's the record of the Step 1/Step 2 audit that decided which of three candidate
project ideas (cantonal mortgage/overheating tracker, rental market tightness/vacancy, and
physical climate risk exposure) actually had obtainable data before any modeling or app code was
written -- and then the concrete findings from building the ingestion pipeline for the winner.

## Why this idea (and not the other two)

Three ideas were audited live against Swiss government data sources before writing any code:

1. **Cantonal Mortgage Affordability & Overheating Tracker** -- rejected. SNB mortgage volumes are
   published nationally / by lending-bank category, not by the canton of the financed property.
   The BFS residential property price index and the BFS rental price index are both published only
   at the national or Grossregion/Gemeindetyp (municipality-type) level -- not by canton. Three of
   the four required series lacked the cantonal granularity the idea's premise needed.
2. **Rental Market Tightness / Vacancy Risk Dashboard** -- **built**. All three required series
   (vacancy rate, rent levels, population/migration) are confirmed available at cantonal or finer
   granularity via real bulk downloads or a documented, no-auth API.
3. **Physical Climate Risk Exposure of the Swiss Property Market** -- rejected. The one series that
   defines the idea -- harmonized natural hazard/flood zoning -- is compiled separately by each of
   the 26 cantons with inconsistent formats and access rules; some federal layers require direct
   order-form requests rather than bulk API access.

## Data sources used

### 1. Vacancy rate (Leerwohnungsziffer) -- `fact_vacancy`

- **Agency / dataset**: BFS (Federal Statistical Office), official vacant-dwelling survey.
  Originally on the STAT-TAB/PxWeb platform; BFS has migrated this dataset to their new SDMX
  platform, **stats.swiss** (dataflow `CH1.LWZ:DF_LWZ_1(1.0.0)`).
- **Access method**: **Real bulk REST API**, confirmed live during a Phase 0 spike.
  `GET https://disseminate.stats.swiss/rest/data/CH1.LWZ,DF_LWZ_1,1.0.0/{key}` with header
  `Accept: application/vnd.sdmx.data+csv;version=1.0.0`. The unfiltered dataflow (`key=all`)
  returns ~7 million rows (~750MB) covering Grossregion/Kanton/Bezirk/Gemeinde x room-count x
  vacancy-type x measure x year -- this project filters the SDMX key to the 26 canton codes
  (confirmed to be the plain 2-letter abbreviations, e.g. `ZH`, `BE`, ... `JU`) and to the "total"
  room-count/vacancy-type codes and the `V` (count) and `PC` (percent) measures, which brings the
  pull down to ~800 usable rows.
- **Granularity**: confirmed available down to **municipality** in the raw dataflow; this project
  loads **canton-level** only, for the practical reason above (see the Canton Detail page and
  "Known simplifications" below).
- **Coverage**: 1995-2025 (vacancy rate/count) for all 26 cantons, annual, reference date June 1.
- **Licence**: Swiss federal open data terms (via stats.swiss / opendata.swiss conventions).
- **Gap found during the initial search, corrected during the audit**: the opendata.swiss dataset
  literally titled "leerwohnungsziffer-nach-gemeinde" is **not** this national series -- it's
  Kanton Zug's own re-publication of just its 11 municipalities. The real national dataset sits
  under different BFS dataset slugs / the SDMX dataflow above.

### 2. Rent levels by canton -- `fact_rent`

- **Agency / dataset**: BFS Strukturerhebung (structural survey), table T 09.03.03.01,
  "Durchschnittlicher Mietpreis nach Zimmerzahl und Kanton" (average rent by room count and canton).
- **Access method**: **Bulk XLS download**, confirmed live:
  `https://dam-api.bfs.admin.ch/hub/api/dam/assets/36398436/master` (HTTP 200, no auth). The file
  served is the **Italian-language** edition (canton names like "Zurigo", "Berna") -- the asset ID
  did not respond to an `Accept-Language: de` header. The ingestion code doesn't need the language
  to match, since canton rows appear in fixed BFS canton-number order (row 8 = canton 1 ... row 33
  = canton 26) in every sheet, so cantons are matched positionally rather than by name.
- **Granularity**: cantonal, broken down by room count (Total, 1, 2, 3, 4, 5, 6+ rooms).
- **Coverage**: one sheet per year, 2010-2024 (15 years), all 26 cantons + a national total row.
- **Licence**: BFS/opendata.swiss open data terms.
- **Gaps / caveats**: this is a **cross-sectional structural survey**, not a continuous monthly
  index -- treat year-to-year changes as discrete survey-wave snapshots, not a smooth trend. BFS
  itself flags that methodology changes in 2015 and 2018 limit comparability with earlier years.
  Some canton/room-count/year cells are suppressed (`X` in the source, loaded as `NULL`) where the
  survey had fewer than 50 observations.

### 3. Population & migration by canton -- `fact_population`, `fact_migration`

- **Agency / dataset**: BFS STAT-TAB PxWeb API, cube `px-x-0102020000_101`, "Demografische Bilanz
  nach Kanton" (demographic balance by canton).
- **Access method**: **Real, documented, no-auth API.**
  `POST https://www.pxweb.bfs.admin.ch/api/v1/de/px-x-0102020000_101/px-x-0102020000_101.px`
  with a JSON PxWeb query body, `response.format=csv`. Confirmed live with real returned values
  (spot-checked against known Zurich canton population ~1.6M in 2024). Response is
  **cp1252-encoded**, not UTF-8 -- handled explicitly in the ingestion code.
- **Granularity**: cantonal (this single cube also has national and by-age/by-civil-status cuts,
  not used here).
- **Coverage**: 1971-2024, annual, all 26 cantons. One cube provides both population stock
  (`Bestand am 1. Januar` / `Bestand am 31. Dezember`, used for `fact_population`) and migration
  flow components (`Einwanderung`, `Auswanderung`, `Wanderungssaldo`, used for `fact_migration`).
- **Licence**: BFS/opendata.swiss open data terms, no authentication or registration required.
- **Gaps found**: the dataset name cited in the original brief ("bevolkerungsstatistik-einwohner"
  on opendata.swiss) turned out to be a 100m-grid **geodata** product (GEOSTAT), not a canton
  table -- the PxWeb cube above is the correct vehicle and was used instead.

### 3b. Vacancy rate by district -- `fact_vacancy_district` (extension, added after initial build)

- **Agency / dataset**: same BFS/stats.swiss SDMX dataflow as `fact_vacancy` (`CH1.LWZ:DF_LWZ_1`),
  one geography level finer -- district (Bezirk) instead of canton.
- **Access method**: same confirmed-live SDMX REST endpoint, same `V`/`PC` measures and `_T`/`_T`
  room-count/vacancy-type filter, just keyed to the 155 district codes instead of the 26 canton
  codes. District codes (e.g. `B_101`) and names were extracted once from the dataflow's own SDMX
  structure metadata -- every code in the `CL_KT_BEZ_GDE_SNAP` codelist whose `Parent` reference is
  a canton abbreviation -- into `config/districts.csv`.
- **Why this and not full municipality-level**: the fully unfiltered dataflow (every room-size x
  vacancy-type x measure x geography level, ~7M rows / ~750MB) was originally assumed to make any
  finer-than-canton geography impractical. That assumption was wrong: applying the same
  totals-only filter already used for cantons, but leaving geography unfiltered, pulls **all**
  levels (Grossregion + Kanton + Bezirk + Gemeinde) at once in **16MB / 142,105 rows** -- trivial.
  The real constraint at municipality level isn't file size, it's that Swiss municipalities merge
  often (the codelist carries ~2,479 historical municipality codes going back to 1995, many now
  defunct), so a correct `dim_municipality` needs merger-aware historization to avoid vacancy trend
  lines silently breaking at merger boundaries. District geography doesn't have that problem --
  BFS's own hierarchy treats it as stable -- so it was the extension actually built.
- **Granularity**: 155 districts (some cantons without an administrative district layer, e.g.
  Appenzell Innerrhoden and Geneva, have a single pseudo-district standing in for the whole canton).
- **Coverage**: 1995-2025, though not every district has data in every year (143 of 155 codes have
  at least one non-null observation -- some codes are historical-only, from before a reorganization).
- **Licence**: same as `fact_vacancy`.

### 4. National rental price index (context only) -- `fact_mietpreisindex_national` (unpopulated)

- **Agency / dataset**: BFS Mietpreisindex, part of the national Landesindex der Konsumentenpreise
  (LIK/CPI).
- **Status**: **not wired up.** No bulk CSV/API endpoint for this specific sub-index could be
  confirmed within this project's scope -- it isn't on the BFS STAT-TAB/PxWeb catalog (checked, no
  matching cube found), and opendata.swiss's package API (`opendata.swiss/api/3/action/...`)
  returned HTTP 403 to automated requests throughout this audit (Cloudflare-protected). Per the
  project's rule of documenting manual steps rather than scraping, this table is left empty; the
  schema slot exists for anyone who wants to complete it later.
- **Manual source**: https://www.bfs.admin.ch/bfs/de/home/statistiken/preise/mieten/index.html
- Even if wired up, BFS itself states this index is **national only** -- "die vierteljährliche
  Erhebung... lässt keine interregionalen Mietpreisvergleiche zu" (no regional/cantonal
  comparison possible) -- so it would only ever serve as context, never as a cantonal comparison.

### 5. Canton boundary geometry (map rendering only)

- **Source**: `swiss-maps` npm package (`interactivethings/swiss-maps`), which packages BFS's own
  official generalized boundary data. Fetched once (`unpkg.com/swiss-maps@4.7.0/2025/ch-combined.json`,
  TopoJSON) and converted to a static `config/cantons.geojson` via GDAL's TopoJSON driver
  (through geopandas), keyed by the same `kt_id` (1-26) used everywhere else in this project.
  This is a build-time asset, not part of the live data pipeline.

## Known simplifications (see also README limitations section)

- **Vacancy is loaded at canton and district level, not municipality**, despite the source
  supporting municipality granularity. Unlike the original assumption, this is no longer a file
  size problem (see the `fact_vacancy_district` entry above) -- it's a data-modeling one:
  municipality codes churn as communes merge, and doing that properly needs a historicized
  `dim_municipality`, which is scoped out as a distinct follow-up, not bundled into this pass.
- **Rent is a cross-sectional survey**, shown as discrete markers per wave in the app, never
  interpolated into a smooth line.
- **National rent index is unpopulated** (see above) -- the app never claims cross-cantonal rent
  index comparisons that BFS itself doesn't publish.
