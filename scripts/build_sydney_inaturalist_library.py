#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import math
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.opportunity_database import OpportunityDatabase
from app.photo_dataset.inaturalist_connector import normalize_observation, search_observations
from app.photo_dataset.quality_labeler import inaturalist_quality_label


SPOTS_PATH = ROOT / "data" / "photo_spots.json"


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371000
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return round(radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 1)


async def run(args: argparse.Namespace) -> int:
    db = OpportunityDatabase()
    run_id = f"sydney_inat_{uuid.uuid4().hex}"
    spots = json.loads(SPOTS_PATH.read_text(encoding="utf-8"))[: args.max_spots]
    by_spot = {}
    inserted = 0
    skipped = 0
    failures = []
    seen_observations = set()
    for spot in spots:
        spot_inserted = 0
        for page in range(1, args.pages_per_spot + 1):
            payload = await search_observations(spot["lat"], spot["lng"], args.radius_km, args.per_page, page)
            for raw in payload.get("results", []):
                if spot_inserted >= args.target_per_spot:
                    break
                item = normalize_observation(raw)
                if item is None:
                    skipped += 1
                    continue
                key = (item["source"], item["source_photo_id"])
                try:
                    item["payload"]["spot_id"] = spot["spot_id"]
                    item["payload"]["spot_name"] = spot["name"]
                    if key not in seen_observations:
                        db.upsert_photo_observation(item)
                        label, score, label_source, label_payload = inaturalist_quality_label(item)
                        label_payload.update({"spot_id": spot["spot_id"], "spot_name": spot["name"]})
                        db.upsert_quality_label(item["source"], item["source_photo_id"], label, score, label_source, label_payload)
                        seen_observations.add(key)
                        inserted += 1
                    db.upsert_spot_photo_sample(
                        spot["spot_id"],
                        item["source"],
                        item["source_photo_id"],
                        distance_m=distance_m(spot["lat"], spot["lng"], item["lat"], item["lng"]),
                        payload={"spot_id": spot["spot_id"], "spot_name": spot["name"], "radius_km": args.radius_km},
                    )
                    spot_inserted += 1
                except Exception as exc:
                    failures.append({"spot_id": spot["spot_id"], "photo_id": item.get("source_photo_id"), "error": str(exc)})
            if spot_inserted >= args.target_per_spot:
                break
        by_spot[spot["spot_id"]] = {"name": spot["name"], "inserted": spot_inserted}
    status = "completed" if not failures else "completed_with_failures"
    result = {"inserted": inserted, "skipped": skipped, "by_spot": by_spot, "failures": failures[:50], "stats": db.stats()}
    db.insert_cold_start_run(run_id, "sydney_10_spot_inaturalist_library", status, result)
    print(json.dumps({"run_id": run_id, "status": status, **result}, ensure_ascii=False, indent=2))
    return 0 if inserted >= args.max_spots * args.min_per_spot and status == "completed" else 3


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Build Sydney multi-spot iNaturalist photo library.")
    p.add_argument("--max-spots", type=int, default=10)
    p.add_argument("--target-per-spot", type=int, default=500)
    p.add_argument("--min-per-spot", type=int, default=500)
    p.add_argument("--pages-per-spot", type=int, default=3)
    p.add_argument("--per-page", type=int, default=200)
    p.add_argument("--radius-km", type=float, default=2)
    return p


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parser().parse_args())))
