#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sqlite3
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.opportunity_database import DB_PATH, OpportunityDatabase
from app.spot_repository import distance_m


SPOTS_PATH = ROOT / "data" / "photo_spots.json"


def run(args: argparse.Namespace) -> int:
    db = OpportunityDatabase()
    spots = json.loads(SPOTS_PATH.read_text(encoding="utf-8"))[: args.max_spots]
    assigned = 0
    by_spot = {spot["spot_id"]: {"name": spot["name"], "assigned": 0} for spot in spots}
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("select source, source_photo_id, lat, lng from photo_observations").fetchall()
    for row in rows:
        for spot in spots:
            dist = distance_m(float(row["lat"]), float(row["lng"]), float(spot["lat"]), float(spot["lng"]))
            if dist <= args.radius_m:
                db.upsert_spot_photo_sample(
                    spot["spot_id"],
                    row["source"],
                    row["source_photo_id"],
                    round(dist, 1),
                    {"spot_id": spot["spot_id"], "spot_name": spot["name"], "radius_m": args.radius_m},
                )
                assigned += 1
                by_spot[spot["spot_id"]]["assigned"] += 1
    print(json.dumps({"status": "completed", "assigned": assigned, "by_spot": by_spot, "stats": db.stats()}, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Assign GPS photo observations to all nearby Sydney photo spots.")
    p.add_argument("--max-spots", type=int, default=10)
    p.add_argument("--radius-m", type=int, default=5000)
    return p


if __name__ == "__main__":
    raise SystemExit(run(parser().parse_args()))
