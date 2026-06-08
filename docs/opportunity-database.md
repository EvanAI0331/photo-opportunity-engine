# Photography Opportunity Database

## Purpose

Build a cold-start database of real photo observations around a place, then enrich each observation with historical weather and astronomical context.

Target shape:

```text
Spot + Time + Weather + Photo Evidence
```

## Data Sources

Wikimedia Commons is the preferred photo source:

- Free and keyless
- Open API
- Low legal risk
- Many files include EXIF/common metadata and GPS
- Category based queries, for example `Category:Sydney Opera House`

iNaturalist is recommended for nature, wildlife, birding, and observation photography:

- Free and keyless
- GPS and observation time
- Photos and species context

Flickr remains a legacy optional connector:

- Requires API key
- Not the default factor research source

OpenStreetMap / Overpass:

- viewpoints
- water
- bridges
- coastline

Open-Meteo Archive:

- historical hourly cloud cover
- low/mid/high cloud cover
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
- `photo_spot_context_enrichment`
- `photo_quality_labels`
- `spot_photo_samples`
- `cold_start_runs`

Runtime databases are ignored by git and release packages.

## Wikimedia Commons Run

```bash
python3 scripts/cold_start_commons.py \
  --place-key sydney_opera_house \
  --category "Category:Sydney Opera House" \
  --pages 1 \
  --per-page 50 \
  --enrich-limit 25
```

Suggested categories:

- `Category:Sydney Opera House`
- `Category:Sydney Harbour Bridge`
- `Category:Bondi Beach`

## iNaturalist Run

```bash
python3 scripts/cold_start_inaturalist.py \
  --place-key sydney_nature \
  --lat -33.8568 \
  --lng 151.2153 \
  --radius-km 10 \
  --pages 1 \
  --per-page 50 \
  --enrich-limit 25
```

## Legacy Flickr Run

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

Requires `FLICKR_API_KEY`.

## Factor Research

The factor research loop reads spot-photo context rows joined with quality labels, then updates:

```text
data/factor_registry.json
```

Run:

```bash
python3 scripts/factor_research_report.py
```

Initial fields:

```json
{
  "factor_id": "sunset_high_cloud_clear_horizon_v1",
  "subject": "sunset_landscape",
  "conditions": [],
  "hit_rate": 0.0,
  "lift": 0.0,
  "false_alert_rate": 0.0,
  "status": "candidate"
}
```

Current quality labels are heuristics:

- Wikimedia Commons: metadata completeness + image dimensions
- iNaturalist: favorites + photo count
- Flickr legacy: views + favorites

Validation unit:

```text
spot_id + source + source_photo_id
```

This keeps spot-specific features such as `direction_match_score`, `travel_cost_score`, and `spot_subject_match_score` tied to the correct camera position. Landscape factors admit Wikimedia Commons and future `user_photo` labels by default; iNaturalist labels are reserved for nature/wildlife/birding style subjects unless a factor explicitly changes that policy.

Replace these with manual scoring or an aesthetic model when available.

## Background Enrichment

For large photo libraries, run context enrichment through the FastAPI backend so the work can continue while you inspect progress:

```bash
curl -X POST "http://127.0.0.1:8001/photo-library/enrichment/start?batch_size=20&sleep_seconds=1&subject=sunset_landscape"
curl "http://127.0.0.1:8001/photo-library/enrichment/status"
curl "http://127.0.0.1:8001/opportunity-db/stats"
```

The worker processes only `spot_photo_samples` with no existing spot context row. Rows marked `failed` are preserved as evidence instead of being silently retried forever.

## Agent-Guided Factor Sampling

Generate coverage over known spots and historical hourly windows:

```bash
python3 scripts/generate_factor_samples.py \
  --lat -33.8568 \
  --lng 151.2153 \
  --radius-m 3000 \
  --max-spots 3 \
  --days 7 \
  --output data/generated_factor_samples.json
```

These samples are for factor coverage and hypothesis generation. Real factor validation still requires photo labels from Wikimedia Commons, iNaturalist, or manually labeled photos.
