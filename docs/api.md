# API

Start:

```bash
uvicorn app.main:app --reload --port 8000
```

Current verified local port:

```bash
uvicorn app.main:app --port 8001
```

Health:

```bash
curl http://127.0.0.1:8000/health
```

Opportunity:

```bash
curl -X POST http://127.0.0.1:8000/opportunity \
  -H 'Content-Type: application/json' \
  -d '{
    "location": {"lat": -33.8568, "lng": 151.2153},
    "time": "2026-06-08T17:12:00+10:00",
    "radius_m": 3000,
    "subject": "sunset_landscape"
  }'
```

The endpoint returns connector evidence, photographic features, opportunity score, and a SpecX-governed `agent_decision_packet`.

This endpoint is not the Agent. It prepares evidence for the LLM-backed Agent contract.

## Harness Loop

Run one persisted opportunity check:

```bash
curl -X POST http://127.0.0.1:8001/loop/run-once \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "default",
    "location": {"lat": -33.8568, "lng": 151.2153},
    "radius_m": 3000,
    "subject": "sunset_landscape"
  }'
```

Start the 15-minute nearby loop:

```bash
curl -X POST http://127.0.0.1:8001/loop/start-15m \
  -H 'Content-Type: application/json' \
  -d '{
    "user_id": "default",
    "location": {"lat": -33.8568, "lng": 151.2153},
    "radius_m": 3000,
    "subject": "sunset_landscape",
    "interval_seconds": 900
  }'
```

Check loop state:

```bash
curl http://127.0.0.1:8001/loop/status
```

Stop the loop:

```bash
curl -X POST http://127.0.0.1:8001/loop/stop
```

Persisted tables live in:

```text
data/photo_memory.sqlite3
```
