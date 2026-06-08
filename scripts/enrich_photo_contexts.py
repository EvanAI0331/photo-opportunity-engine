#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.astronomy_connector import fetch_astronomy
from app.historical_weather_connector import fetch_historical_weather
from app.opportunity_database import DB_PATH, OpportunityDatabase
from app.opportunity_engine import build_features


async def run(args: argparse.Namespace) -> int:
    db = OpportunityDatabase()
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            select o.source, o.source_photo_id, o.lat, o.lng, o.taken_at, s.payload_json as spot_payload
            from photo_observations o
            left join photo_context_enrichment e
              on e.source = o.source and e.source_photo_id = o.source_photo_id and e.status = 'enriched'
            left join spot_photo_samples s
              on s.source = o.source and s.source_photo_id = o.source_photo_id
            where e.source_photo_id is null
            group by o.source, o.source_photo_id
            limit ?
            """,
            (args.limit,),
        ).fetchall()
    enriched = 0
    failed = 0
    failures = []
    for row in rows:
        try:
            when = datetime.fromisoformat(str(row["taken_at"]).replace("Z", "+00:00"))
            weather = await fetch_historical_weather(float(row["lat"]), float(row["lng"]), when)
            astronomy = await fetch_astronomy(float(row["lat"]), float(row["lng"]), when)
            spot_payload = json.loads(row["spot_payload"]) if row["spot_payload"] else {}
            spot = {"spot_id": spot_payload.get("spot_id"), "name": spot_payload.get("spot_name"), "lat": float(row["lat"]), "lng": float(row["lng"]), "best_directions_deg": []}
            features = build_features(weather, astronomy, {}, [spot], when, args.subject)
            db.upsert_context_enrichment(row["source"], row["source_photo_id"], "enriched", weather, astronomy, features)
            enriched += 1
        except Exception as exc:
            db.upsert_context_enrichment(row["source"], row["source_photo_id"], "failed", None, None, None, "context_enrichment_failed")
            failures.append({"source": row["source"], "source_photo_id": row["source_photo_id"], "error": str(exc)})
            failed += 1
    print(json.dumps({"status": "completed", "requested": args.limit, "enriched": enriched, "failed": failed, "failures": failures[:20], "stats": db.stats()}, ensure_ascii=False, indent=2))
    return 0 if failed == 0 else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Batch enrich photo observations with weather, astronomy, and factor features.")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--subject", default="sunset_landscape")
    return p


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parser().parse_args())))
