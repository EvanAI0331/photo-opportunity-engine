#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.photo_library_enrichment import enrich_batch


async def run(args: argparse.Namespace) -> int:
    result = await enrich_batch(args.limit, args.subject)
    print(json.dumps({"status": "completed", "requested": args.limit, **result}, ensure_ascii=False, indent=2))
    return 0 if result["failed"] == 0 else 1


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Batch enrich photo observations with weather, astronomy, and factor features.")
    p.add_argument("--limit", type=int, default=500)
    p.add_argument("--subject", default="sunset_landscape")
    return p


if __name__ == "__main__":
    raise SystemExit(asyncio.run(run(parser().parse_args())))
