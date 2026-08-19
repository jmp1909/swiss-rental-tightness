# Data Sources

Every number in this app traces back to one of the sources below -- all official Swiss federal
statistics, pulled programmatically via a real bulk download or documented API, never scraped.

## Vacancy rate -- `fact_vacancy`, `fact_vacancy_district`

- **Source**: Federal Statistical Office (BFS), official vacant-dwelling survey (Leerwohnungsziffer),
  published via BFS's SDMX platform, [stats.swiss](https://stats.swiss) (dataflow `CH1.LWZ:DF_LWZ_1`).
- **Access**: bulk REST API, `GET https://disseminate.stats.swiss/rest/data/CH1.LWZ,DF_LWZ_1,1.0.0/{key}`,
  no authentication.
- **Granularity**: canton (26) and district/Bezirk (143 with current data, of 155 known codes).
  Municipality-level is available in the same source but not loaded -- see *Limitations* below.
- **Coverage**: 1995-2025, annual, reference date June 1.
- **Licence**: Swiss federal open data terms.

## Rent levels -- `fact_rent`

- **Source**: BFS Strukturerhebung (structural survey), table T 09.03.03.01, "Durchschnittlicher
  Mietpreis nach Zimmerzahl und Kanton" (average rent by room count and canton).
- **Access**: bulk Excel download from `dam-api.bfs.admin.ch`, no authentication.
- **Granularity**: cantonal, by room count (1 through 6+ rooms, plus total).
- **Coverage**: one year per sheet, 2010-2024.
- **Licence**: BFS open data terms.
- **Caveat**: a cross-sectional structural survey, not a continuous index -- BFS flags limited
  comparability across its 2015 and 2018 methodology changes.

## Population & migration -- `fact_population`, `fact_migration`

- **Source**: BFS STAT-TAB PxWeb API, cube `px-x-0102020000_101`, "Demografische Bilanz nach
  Kanton" (demographic balance by canton).
- **Access**: documented REST API, `pxweb.bfs.admin.ch`, no authentication.
- **Granularity**: cantonal. One cube provides both population stock and migration flow components
  (immigration, emigration, net migration).
- **Coverage**: 1971-2024, annual.
- **Licence**: BFS open data terms.

## New dwellings constructed -- `fact_new_dwellings`

- **Source**: BFS STAT-TAB PxWeb API, cube `px-x-0904030000_105`, "Neu erstellte Wohnungen nach
  Grossregion / Kanton / Gemeinde und Anzahl Zimmer" (newly built dwellings).
- **Access**: same documented PxWeb API, no authentication.
- **Granularity**: cantonal.
- **Coverage**: 2013-2024, annual.
- **Licence**: BFS open data terms.
- **Caveat**: this is construction *flow* (dwellings completed that year), used in the tightness
  score as a per-capita construction-intensity signal -- not total dwelling *stock*. A clean bulk
  time series for stock level by canton wasn't available (BFS publishes stock as a full-address
  geodata snapshot per year, not a canton-level series ready for year-over-year comparison).

## Boundary geometry (map rendering only)

- **Cantons**: `interactivethings/swiss-maps` (npm package built from BFS's official generalized
  boundary data), converted once to a static `config/cantons.geojson`.
- **Districts**: BFS's own "Generalisierte Gemeindegrenzen" boundary product (`opendata.swiss`),
  converted once to `config/districts.geojson`, matched to the vacancy data by BFS's official
  district number (e.g. district `101` = Bezirk Affoltern in both sources).
- Both are static, one-time build assets -- not part of the live ingestion pipeline.

## Limitations

- **District-level signals other than vacancy are borrowed from the parent canton.** BFS doesn't
  publish rent, population, or construction data below canton level, so the tightness score's
  demand/supply, rent-level, and rent-growth components use each district's parent canton's value
  for every district in that canton -- flagged in the app, not hidden.
- **Municipality-level vacancy isn't loaded**, though the source supports it. Swiss municipalities
  merge often enough (hundreds of historical codes in the source, many now defunct) that a correct
  municipality dimension needs merger-aware historization -- out of scope for now.
- **Rent is a survey snapshot**, not a continuous index -- shown as discrete yearly points, not
  smoothed. The national rent index (Mietpreisindex, part of the Swiss CPI) isn't included: no
  bulk/API source for it could be confirmed, and it's published nationally only in any case, so it
  couldn't support cantonal comparison even if it were wired up.
- **The tightness score is a heuristic**, not a validated economic index -- see the Market
  Tightness Composite page for the full methodology and adjustable weights.
