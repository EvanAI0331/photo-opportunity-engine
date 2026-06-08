# Lightweight Harness And Persistent Loop

## Boundary

Harness only schedules and constrains:

```text
data collection -> feature calculation -> opportunity scoring -> Agent decision packet -> notification handoff -> feedback record
```

It does not let the LLM run freely. It also does not replace the LLM-backed Agent with script decisions.

## Components

- `app/orchestrator.py`: runs weather, astronomy, geo, spot repository, feature calculation, scoring, and builds the SpecX-governed Agent packet.
- `app/opportunity_loop.py`: runs one-off checks, 15-minute nearby checks, and daily morning digest checks.
- `app/memory_store.py`: SQLite persistence for loop runs, opportunity records, feedback, preferences, and history.
- `app/main.py`: FastAPI routes for opportunity checks, loop control, feedback, and memory reads.

## Persisted Store

SQLite path:

```text
data/photo_memory.sqlite3
```

Tables:

- `user_profile`
- `photo_preferences`
- `ignored_alerts`
- `accepted_alerts`
- `shooting_history`
- `location_favorites`
- `lens_preferences`
- `project_goals`
- `loop_runs`
- `opportunity_records`

## Loop Routes

- `POST /loop/run-once`
- `POST /loop/start-15m`
- `POST /loop/stop`
- `GET /loop/status`
- `POST /loop/daily-morning`
- `GET /memory/opportunities`
- `POST /feedback`
- `POST /shooting-history`

## Current Limitation

The current system prepares a SpecX-governed `agent_decision_packet`; it does not yet call an LLM-backed Agent runtime or notification provider. Until those are connected, final Agent judgment and push delivery must remain explicit handoff steps, not fake completion.
