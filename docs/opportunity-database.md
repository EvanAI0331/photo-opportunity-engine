# Photography Opportunity Database

## Purpose

Build a cold-start database of real photo observations around a place, then enrich each observation with historical weather and astronomical context.

Example target:

```text
Sydney Opera House
radius: 2 km
period: past 5 years
source: Flickr geotagged public photos
```

## Data Sources

Flickr:

- geotagged public photos
- taken time
- latitude / longitude
- views
- tags / owner name
- optional favorites when available

OpenStreetMap / Overpass:

- viewpoints
- water
- bridges
- coastline

Open-Meteo Archive:

- historical hourly cloud cover
- visibility
- humidity
- precipitation
- wind

SunCalc:

- sun position
- moon position
- moon phase
- sunrise / sunset windows

## Database

SQLite path:

```text
data/photo_opportunity.sqlite3
```

Tables:

- `photo_observations`
- `osm_place_features`
- `photo_context_enrichment`
- `cold_start_runs`

Runtime databases are ignored by git and release packages.

## Run

Set Flickr key:

```bash
cp .env.example .env
# fill FLICKR_API_KEY
```

Small verified-style run:

```bash
python3 scripts/cold_start_flickr.py \
  --place-key sydney_opera_house \
  --lat -33.8568 \
  --lng 151.2153 \
  --radius-km 2 \
  --start-date 2021-06-08 \
  --end-date 2026-06-08 \
  --pages 1 \
  --per-page 250 \
  --enrich-limit 25 \
  --text "Sydney Opera House"
```

Scaling note:

- Flickr pages can return up to 500 photos each.
- 100k photos requires pagination and rate-limit-aware batching.
- Historical enrichment should be batched/cached by `(lat_bucket, lng_bucket, hour)`.
- Do not claim completion if Flickr key, pagination, or historical enrichment fails.
