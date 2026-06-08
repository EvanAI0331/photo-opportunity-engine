from __future__ import annotations

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SUNCALC_TOOL = ROOT / "tools" / "suncalc_tool.mjs"


async def fetch_astronomy(lat: float, lng: float, when: datetime) -> dict[str, Any]:
    proc = await asyncio.create_subprocess_exec(
        "node",
        str(SUNCALC_TOOL),
        when.isoformat(),
        str(lat),
        str(lng),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode("utf-8", errors="replace").strip() or "SunCalc failed")
    return json.loads(stdout.decode("utf-8"))
