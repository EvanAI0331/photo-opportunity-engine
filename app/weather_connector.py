from __future__ import annotations

from datetime import datetime
from typing import Any

import httpx


OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HOURLY_FIELDS = [
    "cloud_cover",
    "visibility",
    "relative_humidity_2m",
    "precipitation_probability",
    "wind_speed_10m",
]


async def fetch_weather(lat: float, lng: float, when: datetime) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lng,
        "hourly": ",".join(HOURLY_FIELDS),
        "timezone": "auto",
    }
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
    payload = response.json()
    hourly = payload.get("hourly") or {}
    times = hourly.get("time") or []
    if not times:
        raise ValueError("Open-Meteo response missing hourly time array")

    target_hour = when.replace(minute=0, second=0, microsecond=0)
    target_key = target_hour.strftime("%Y-%m-%dT%H:00")
    try:
        index = times.index(target_key)
    except ValueError:
        index = min(
            range(len(times)),
            key=lambda i: abs(datetime.fromisoformat(times[i]) - target_hour.replace(tzinfo=None)),
        )

    selected = {"time": times[index]}
    for field in HOURLY_FIELDS:
        values = hourly.get(field)
        selected[field] = values[index] if isinstance(values, list) and index < len(values) else None
    selected["units"] = payload.get("hourly_units", {})
    selected["timezone"] = payload.get("timezone")
    return selected
