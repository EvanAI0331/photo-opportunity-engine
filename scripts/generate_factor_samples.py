#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.astronomy_connector import fetch_astronomy
from app.historical_weather_connector import fetch_historical_weather
from app.opportunity_engine import build_features
from app.spot_repository import load_spots


async def run(args: argparse.Namespace) -> int:
    spots = load_spots(args.lat, args.lng, args.radius_m)[: args.max_spots]
    start = datetime.fromisoformat(args.start.replace("Z", "+00:00"))
    hours = args.days * 24
    output = []
    for spot in spots:
        for offset in range(hours):
            when = start + timedelta(hours=offset)
            try:
                weather = await fetch_historical_weather(spot["lat"], spot["lng"], when)
                astronomy = await fetch_astronomy(spot["lat"], spot["lng"], when)
                features = build_features(weather, astronomy, {}, [spot], when, args.subject)
                output.append({"spot_id": spot["spot_id"], "spot_name": spot["name"], "time": when.isoformat(), "features": features})
            except Exception as exc:
                output.append({"spot_id": spot["spot_id"], "spot_name": spot["name"], "time": when.isoformat(), "failure_state": "sample_generation_failed", "error": str(exc)})
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": "completed", "spots": len(spots), "samples": len(output), "output": str(out_path)}, ensure_ascii=False, indent=2))
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Agent-guided factor sample generation over spots and historical hourly windows.")
    p.add_argument("--lat", type=float, required=True)
    p.add_argument("--lng", type=float, required=True)
    p.add_argument("--radius-m", type=int, default=3000)
    p.add_argument("--max-spots", type=int, default=3)
    p.add_argument("--days", type=int, default=7)
    p.add_argument("--start", default=(datetime.now(timezone.utc) - timedelta(days=7)).isoformat())
    p.add_argument("--subject", default="sunset_landscape")
    p.add_argument("--output", default="data/generated_factor_samples.json")
    return p


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parser().parse_args())))
