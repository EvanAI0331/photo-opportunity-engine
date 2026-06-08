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
from app.photo_dataset.quality_labeler import commons_quality_label
from app.photo_dataset.wikimedia_commons_connector import geosearch_files, normalize_commons_page


SPOTS_PATH = ROOT / "data" / "photo_spots.json"


async def run(args: argparse.Namespace) -> int:
    db = OpportunityDatabase()
    run_id = f"sydney_library_{uuid.uuid4().hex}"
    spots = json.loads(SPOTS_PATH.read_text(encoding="utf-8"))[: args.max_spots]
    by_spot = {}
    inserted = 0
    enriched = 0
    skipped = 0
    failures = []
    for spot in spots:
        spot_inserted = 0
        spot_enriched = 0
        continuation = None
        for _ in range(args.pages_per_spot):
            payload = await geosearch_files(spot["lat"], spot["lng"], args.radius_m, args.per_page, continuation)
            pages = (payload.get("query") or {}).get("pages") or {}
            for page in pages.values():
                if spot_inserted >= args.target_per_spot:
                    break
                item = normalize_commons_page(page)
                if item is None:
                    skipped += 1
                    continue
                try:
                    item["payload"]["spot_id"] = spot["spot_id"]
                    item["payload"]["spot_name"] = spot["name"]
                    db.upsert_photo_observation(item)
                    label, score, label_source, label_payload = commons_quality_label(item)
                    label_payload.update({"spot_id": spot["spot_id"], "spot_name": spot["name"]})
                    db.upsert_quality_label(item["source"], item["source_photo_id"], label, score, label_source, label_payload)
                    inserted += 1
                    spot_inserted += 1
                    if args.enrich_per_spot and spot_enriched >= args.enrich_per_spot:
                        continue
                    when = datetime.fromisoformat(item["taken_at"])
                    weather = await fetch_historical_weather(item["lat"], item["lng"], when)
                    astronomy = await fetch_astronomy(item["lat"], item["lng"], when)
                    features = build_features(weather, astronomy, {}, [spot], when, args.subject)
                    db.upsert_context_enrichment(item["source"], item["source_photo_id"], "enriched", weather, astronomy, features)
                    enriched += 1
                    spot_enriched += 1
                except Exception as exc:
                    failures.append({"spot_id": spot["spot_id"], "photo_id": item.get("source_photo_id"), "error": str(exc)})
                    db.upsert_context_enrichment(item["source"], item["source_photo_id"], "failed", None, None, None, "context_enrichment_failed")
            continuation = (payload.get("continue") or {}).get("ggscontinue")
            if not continuation or spot_inserted >= args.target_per_spot:
                break
        by_spot[spot["spot_id"]] = {"name": spot["name"], "inserted": spot_inserted, "enriched": spot_enriched}
    status = "completed" if not failures else "completed_with_failures"
    result = {"inserted": inserted, "enriched": enriched, "skipped": skipped, "by_spot": by_spot, "failures": failures[:50], "stats": db.stats()}
    db.insert_cold_start_run(run_id, "sydney_10_spot_photo_library", status, result)
    print(json.dumps({"run_id": run_id, "status": status, **result}, ensure_ascii=False, indent=2))
    if inserted < args.max_spots * args.min_per_spot:
        return 3
    return 0 if status == "completed" else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build Sydney multi-spot Wikimedia Commons photo library.")
    p.add_argument("--max-spots", type=int, default=10)
    p.add_argument("--target-per-spot", type=int, default=500)
    p.add_argument("--min-per-spot", type=int, default=500)
    p.add_argument("--pages-per-spot", type=int, default=4)
    p.add_argument("--per-page", type=int, default=250)
    p.add_argument("--radius-m", type=int, default=1500)
    p.add_argument("--enrich-per-spot", type=int, default=25)
    p.add_argument("--subject", default="sunset_landscape")
    return p


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parser().parse_args())))
