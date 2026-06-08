#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.astronomy_connector import fetch_astronomy
from app.historical_weather_connector import fetch_historical_weather
from app.opportunity_database import OpportunityDatabase
from app.opportunity_engine import build_features
from app.photo_dataset.inaturalist_connector import normalize_observation, search_observations
from app.photo_dataset.quality_labeler import inaturalist_quality_label


async def run(args: argparse.Namespace) -> int:
    db = OpportunityDatabase()
    run_id = f"inat_{uuid.uuid4().hex}"
    inserted = 0
    enriched = 0
    skipped = 0
    failures = []
    for page in range(1, args.pages + 1):
        payload = await search_observations(args.lat, args.lng, args.radius_km, args.per_page, page)
        for raw in payload.get("results", []):
            item = normalize_observation(raw)
            if item is None:
                skipped += 1
                continue
            try:
                db.upsert_photo_observation(item)
                label, score, label_source, label_payload = inaturalist_quality_label(item)
                db.upsert_quality_label(item["source"], item["source_photo_id"], label, score, label_source, label_payload)
                inserted += 1
                if args.enrich_limit and enriched >= args.enrich_limit:
                    continue
                when = datetime.fromisoformat(item["taken_at"].replace("Z", "+00:00"))
                weather = await fetch_historical_weather(item["lat"], item["lng"], when)
                astronomy = await fetch_astronomy(item["lat"], item["lng"], when)
                features = build_features(weather, astronomy, {}, [], when, args.subject)
                db.upsert_context_enrichment(item["source"], item["source_photo_id"], "enriched", weather, astronomy, features)
                enriched += 1
            except Exception as exc:
                failures.append({"photo_id": item.get("source_photo_id"), "error": str(exc)})
        if page >= int((payload.get("total_results") or 0) / max(args.per_page, 1)) + 1:
            break
    status = "completed" if not failures else "completed_with_failures"
    result = {"inserted": inserted, "enriched": enriched, "skipped": skipped, "failures": failures[:50], "stats": db.stats()}
    db.insert_cold_start_run(run_id, args.place_key, status, result)
    print(json.dumps({"run_id": run_id, "status": status, **result}, ensure_ascii=False, indent=2))
    return 0 if status == "completed" else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Cold-start nature/wildlife observations from iNaturalist.")
    p.add_argument("--place-key", required=True)
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--radius-km", type=float, default=10)
    p.add_argument("--pages", type=int, default=1)
    p.add_argument("--per-page", type=int, default=50)
    p.add_argument("--enrich-limit", type=int, default=25)
    p.add_argument("--subject", default="wildlife")
    return p


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parser().parse_args())))
