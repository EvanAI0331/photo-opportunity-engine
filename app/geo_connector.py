from __future__ import annotations

from typing import Any

import httpx


OVERPASS_URL = "https://overpass-api.de/api/interpreter"


def build_query(lat: float, lng: float, radius_m: int) -> str:
    return f"""
[out:json][timeout:25];
(
  node["tourism"="viewpoint"](around:{radius_m},{lat},{lng});
  way["tourism"="viewpoint"](around:{radius_m},{lat},{lng});
  node["natural"="water"](around:{radius_m},{lat},{lng});
  way["natural"="water"](around:{radius_m},{lat},{lng});
  way["man_made"="bridge"](around:{radius_m},{lat},{lng});
  way["bridge"](around:{radius_m},{lat},{lng});
  way["natural"="coastline"](around:{radius_m},{lat},{lng});
);
out center tags;
"""


async def fetch_geo(lat: float, lng: float, radius_m: int) -> dict[str, Any]:
    query = build_query(lat, lng, radius_m)
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            OVERPASS_URL,
            data={"data": query},
            headers={"User-Agent": "photo-opportunity-engine/0.1"},
        )
        response.raise_for_status()
    payload = response.json()
    elements = payload.get("elements") or []
    summary = {
        "viewpoints": 0,
        "water": 0,
        "bridges": 0,
        "coastline": 0,
        "elements": [],
    }
    for item in elements[:80]:
        tags = item.get("tags") or {}
        if tags.get("tourism") == "viewpoint":
            summary["viewpoints"] += 1
        if tags.get("natural") == "water":
            summary["water"] += 1
        if tags.get("man_made") == "bridge" or "bridge" in tags:
            summary["bridges"] += 1
        if tags.get("natural") == "coastline":
            summary["coastline"] += 1
        center = item.get("center") or {"lat": item.get("lat"), "lon": item.get("lon")}
        summary["elements"].append(
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "name": tags.get("name"),
                "tags": {key: tags[key] for key in sorted(tags) if key in {"name", "tourism", "natural", "man_made", "bridge"}},
                "lat": center.get("lat"),
                "lng": center.get("lon"),
            }
        )
    return summary
