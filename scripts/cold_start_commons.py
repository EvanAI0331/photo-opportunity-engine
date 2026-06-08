#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.opportunity_database import OpportunityDatabase
from app.photo_dataset.quality_labeler import commons_quality_label
from app.photo_dataset.wikimedia_commons_connector import category_files, normalize_commons_page


async def run(args: argparse.Namespace) -> int:
    db = OpportunityDatabase()
    run_id = f"commons_{uuid.uuid4().hex}"
    inserted = 0
    skipped = 0
    failures = []
    continuation = None
    for _ in range(args.pages):
        payload = await category_files(args.category, limit=args.per_page, cmcontinue=continuation)
        pages = (payload.get("query") or {}).get("pages") or {}
        for page in pages.values():
            item = normalize_commons_page(page)
            if item is None:
                skipped += 1
                continue
            try:
                db.upsert_photo_observation(item)
                label, score, label_source, label_payload = commons_quality_label(item)
                db.upsert_quality_label(item["source"], item["source_photo_id"], label, score, label_source, label_payload)
                inserted += 1
            except Exception as exc:
                failures.append({"photo_id": item.get("source_photo_id"), "error": str(exc)})
        continuation = (payload.get("continue") or {}).get("gcmcontinue")
        if not continuation:
            break
    status = "completed" if not failures else "completed_with_failures"
    result = {"inserted": inserted, "skipped": skipped, "failures": failures[:50], "stats": db.stats()}
    db.insert_cold_start_run(run_id, args.place_key, status, result)
    print(json.dumps({"run_id": run_id, "status": status, **result}, ensure_ascii=False, indent=2))
    return 0 if status == "completed" else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Cold-start factor validation photos from Wikimedia Commons.")
    p.add_argument("--place-key", required=True)
    p.add_argument("--category", required=True)
    p.add_argument("--pages", type=int, default=1)
    p.add_argument("--per-page", type=int, default=50)
    return p


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parser().parse_args())))
