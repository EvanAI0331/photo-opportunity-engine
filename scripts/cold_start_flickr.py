#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from datetime import date
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.flickr_connector import FlickrConnectorError
from app.flickr_connector import search_geotagged_photos
from app.opportunity_database import OpportunityDatabase


async def run(args: argparse.Namespace) -> int:
    db = OpportunityDatabase()
    run_id = f"cold_{uuid.uuid4().hex}"
    inserted = 0
    failures = []
    for page in range(1, args.pages + 1):
        try:
            photos = await search_geotagged_photos(
                lat=args.lat,
                lng=args.lng,
                radius_km=args.radius_km,
                min_taken_date=date.fromisoformat(args.start_date),
                max_taken_date=date.fromisoformat(args.end_date),
                page=page,
                per_page=args.per_page,
                text=args.text,
            )
        except FlickrConnectorError as exc:
            payload = {"inserted": inserted, "failure_state": "blocked_flickr_api_unavailable", "error": str(exc), "stats": db.stats()}
            db.insert_cold_start_run(run_id, args.place_key, "blocked", payload)
            print(json.dumps({"run_id": run_id, "status": "blocked", **payload}, ensure_ascii=False, indent=2))
            return 2
        for photo in photos.get("photo", []):
            try:
                lat = float(photo["latitude"])
                lng = float(photo["longitude"])
                taken_at = photo.get("datetaken")
                if not taken_at:
                    raise ValueError("missing datetaken")
                item = {
                    "source": "flickr",
                    "source_photo_id": str(photo["id"]),
                    "lat": lat,
                    "lng": lng,
                    "taken_at": taken_at,
                    "views": int(photo["views"]) if str(photo.get("views", "")).isdigit() else None,
                    "favorites": int(photo["favorites"]) if str(photo.get("favorites", "")).isdigit() else None,
                    "owner_name": photo.get("ownername"),
                    "tags": photo.get("tags"),
                    "payload": photo,
                }
                db.upsert_photo_observation(item)
                quality_score = compute_quality_score(item)
                db.upsert_quality_label(
                    "flickr",
                    str(photo["id"]),
                    int(quality_score >= 0.65),
                    quality_score,
                    "flickr_views_favorites_heuristic_v1",
                    {"views": item.get("views"), "favorites": item.get("favorites")},
                )
                inserted += 1
            except Exception as exc:
                failures.append({"photo_id": photo.get("id"), "error": str(exc)})
        if page >= int(photos.get("pages") or page):
            break
    status = "completed" if not failures else "completed_with_failures"
    payload = {"inserted": inserted, "failures": failures[:50], "stats": db.stats()}
    db.insert_cold_start_run(run_id, args.place_key, status, payload)
    print(json.dumps({"run_id": run_id, "status": status, **payload}, ensure_ascii=False, indent=2))
    return 0 if status == "completed" else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Cold-start a photography opportunity database from Flickr metadata.")
    p.add_argument("--place-key", required=True)
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--radius-km", type=float, default=2)
    p.add_argument("--start-date", required=True)
    p.add_argument("--end-date", required=True)
    p.add_argument("--pages", type=int, default=1)
    p.add_argument("--per-page", type=int, default=250)
    p.add_argument("--text")
    return p


def compute_quality_score(item: dict) -> float:
    views = item.get("views") or 0
    favorites = item.get("favorites") or 0
    view_score = min(1.0, views / 1000)
    favorite_score = min(1.0, favorites / 100)
    return round(max(view_score * 0.7, favorite_score * 0.9), 3)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parser().parse_args())))
