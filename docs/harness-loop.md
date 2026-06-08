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

The current system calls the LLM-backed Agent runtime when `MINIMAX_API_KEY` is configured. Notification delivery is still an explicit handoff step and must not be reported as completed until a real notification provider is connected.

The loop records connector errors and missing evidence in the persisted payload so blocked runs can be audited.
