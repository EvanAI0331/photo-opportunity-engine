# Photo Opportunity Engine

Location-Time-Subject photography opportunity engine.

It collects weather, astronomy, geo, and local spot evidence, converts them into photography features, scores the opportunity, and prepares a SpecX-governed packet for an LLM-backed Agent decision.

## Setup

```bash
python3 -m pip install -r requirements.txt
npm install
cp .env.example .env
```

Configure `.env`:

```text
MINIMAX_API_KEY=...
MINIMAX_BASE_URL=https://api.minimaxi.com/v1
MINIMAX_MODEL=MiniMax-M3
MINIMAX_THINKING_TYPE=disabled
```

`.env` is ignored by git and is not included in release packages.

## Run

```bash
npm run start
```

API:

```text
http://127.0.0.1:8001
```

## Verify SpecX

```bash
npm run specx
```

## Harness

- `app/orchestrator.py`: data collection, feature extraction, scoring, Agent packet.
- `app/opportunity_loop.py`: manual checks, 15-minute loop, daily digest.
- `app/memory_store.py`: SQLite persistence.
- `app/agent_runtime.py`: MiniMax-M3 Agent runtime, thinking disabled.

The score engine is not the Agent. Final notification judgment belongs to the LLM-backed Agent runtime under the SpecX contract.

## Cold-Start Opportunity Database

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

Requires `FLICKR_API_KEY`. See [docs/opportunity-database.md](docs/opportunity-database.md).

## Factor Research

```bash
python3 scripts/factor_research_report.py
```

The first version validates candidate photography factors against persisted `opportunity_records`.
It does not train a model. Low sample size means factors remain `candidate`.
