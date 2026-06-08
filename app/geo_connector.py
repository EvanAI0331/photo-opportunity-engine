from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx


ROOT = Path(__file__).resolve().parents[1]
CACHE_PATH = ROOT / "data" / "osm_geo_cache.json"
OVERPASS_ENDPOINTS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]


def cache_key(lat: float, lng: float, radius_m: int) -> str:
    return f"{round(lat, 4)}:{round(lng, 4)}:{radius_m}"


def load_cache() -> dict[str, Any]:
    if not CACHE_PATH.exists():
        return {}
    return json.loads(CACHE_PATH.read_text(encoding="utf-8"))


def save_cache(cache: dict[str, Any]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def count_query(kind: str, lat: float, lng: float, radius_m: int) -> str:
    selectors = {
        "viewpoints": f'node["tourism"="viewpoint"](around:{radius_m},{lat},{lng});way["tourism"="viewpoint"](around:{radius_m},{lat},{lng});',
        "water": f'node["natural"="water"](around:{radius_m},{lat},{lng});way["natural"="water"](around:{radius_m},{lat},{lng});',
        "bridges": f'way["man_made"="bridge"](around:{radius_m},{lat},{lng});way["bridge"](around:{radius_m},{lat},{lng});',
        "coastline": f'way["natural"="coastline"](around:{radius_m},{lat},{lng});',
    }
    return f'[out:json][timeout:20];({selectors[kind]});out count;'


def sample_query(lat: float, lng: float, radius_m: int) -> str:
    return f"""
[out:json][timeout:20];
(
  node["tourism"="viewpoint"](around:{radius_m},{lat},{lng});
  way["tourism"="viewpoint"](around:{radius_m},{lat},{lng});
);
out center tags 20;
"""


async def post_overpass(client: httpx.AsyncClient, query: str) -> tuple[str, dict[str, Any]]:
    errors = []
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = await client.post(
                endpoint,
                data={"data": query},
                headers={"User-Agent": "photo-opportunity-engine/0.1"},
            )
            response.raise_for_status()
            return endpoint, response.json()
        except Exception as exc:
            errors.append({"endpoint": endpoint, "error": str(exc)})
    raise RuntimeError(str(errors))


def parse_count(payload: dict[str, Any]) -> int:
    elements = payload.get("elements") or []
    if not elements:
        return 0
    tags = elements[0].get("tags") or {}
    return int(tags.get("total") or tags.get("nodes") or tags.get("ways") or 0)


def parse_elements(payload: dict[str, Any]) -> list[dict[str, Any]]:
    elements = []
    for item in (payload.get("elements") or [])[:20]:
        tags = item.get("tags") or {}
        center = item.get("center") or {"lat": item.get("lat"), "lon": item.get("lon")}
        elements.append(
            {
                "id": item.get("id"),
                "type": item.get("type"),
                "name": tags.get("name"),
                "tags": {key: tags[key] for key in sorted(tags) if key in {"name", "tourism", "natural", "man_made", "bridge"}},
                "lat": center.get("lat"),
                "lng": center.get("lon"),
            }
        )
    return elements


async def fetch_geo(lat: float, lng: float, radius_m: int) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "endpoint": None,
        "cached": False,
        "partial": False,
        "partial_errors": {},
        "viewpoints": None,
        "water": None,
        "bridges": None,
        "coastline": None,
        "elements": [],
    }
    success_count = 0
    async with httpx.AsyncClient(timeout=35) as client:
        for kind in ("viewpoints", "water", "bridges", "coastline"):
            try:
                endpoint, payload = await post_overpass(client, count_query(kind, lat, lng, radius_m))
                summary["endpoint"] = summary["endpoint"] or endpoint
                summary[kind] = parse_count(payload)
                success_count += 1
            except Exception as exc:
                summary["partial"] = True
                summary["partial_errors"][kind] = str(exc)
        try:
            endpoint, payload = await post_overpass(client, sample_query(lat, lng, radius_m))
            summary["endpoint"] = summary["endpoint"] or endpoint
            summary["elements"] = parse_elements(payload)
            success_count += 1
        except Exception as exc:
            summary["partial"] = True
            summary["partial_errors"]["elements"] = str(exc)

    key = cache_key(lat, lng, radius_m)
    if success_count == 0:
        cached = load_cache().get(key)
        if isinstance(cached, dict):
            cached = dict(cached)
            cached["cached"] = True
            cached["cache_reason"] = "overpass_live_query_failed"
            cached["live_errors"] = summary["partial_errors"]
            return cached
        raise RuntimeError(f"Overpass query failed on all subqueries: {summary['partial_errors']}")

    for key_name in ("viewpoints", "water", "bridges", "coastline"):
        if summary[key_name] is None:
            summary[key_name] = 0
    cache = load_cache()
    cache[key] = summary
    save_cache(cache)
    return summary
