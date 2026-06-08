from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx

from .time_utils import ensure_timezone_aware, to_timezone


ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
HOURLY_FIELDS = [
    "cloud_cover",
    "cloud_cover_low",
    "cloud_cover_mid",
    "cloud_cover_high",
    "visibility",
    "relative_humidity_2m",
    "precipitation",
    "wind_speed_10m",
]


async def fetch_historical_weather(lat: float, lng: float, when: datetime) -> dict[str, Any]:
    aware_when = ensure_timezone_aware(when)
    day = aware_when.date().isoformat()
    params = {
        "latitude": lat,
        "longitude": lng,
        "start_date": day,
        "end_date": day,
        "hourly": ",".join(HOURLY_FIELDS),
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(ARCHIVE_URL, params=params)
        response.raise_for_status()
    payload = response.json()
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        raise ValueError("Open-Meteo archive response missing hourly time array")
    timezone_name = payload.get("timezone")
    local_when = to_timezone(aware_when, timezone_name if isinstance(timezone_name, str) else None)
    target_hour = local_when.replace(minute=0, second=0, microsecond=0)
    target_key = target_hour.strftime("%Y-%m-%dT%H:00")
    try:
        index = times.index(target_key)
    except ValueError:
        index = min(range(len(times)), key=lambda i: abs(datetime.fromisoformat(times[i]) - target_hour.replace(tzinfo=None)))
    selected = {"time": times[index], "matched_local_hour": target_key, "request_time": aware_when.isoformat()}
    for field in HOURLY_FIELDS:
        values = hourly.get(field)
        selected[field] = values[index] if isinstance(values, list) and index < len(values) else None
    selected["units"] = payload.get("hourly_units", {})
    selected["timezone"] = timezone_name
    return selected
