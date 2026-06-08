from __future__ import annotations

from typing import Any

import httpx


INAT_OBSERVATIONS_URL = "https://api.inaturalist.org/v1/observations"


async def search_observations(lat: float, lng: float, radius_km: float, per_page: int = 50, page: int = 1) -> dict[str, Any]:
    params = {
        "lat": lat,
        "lng": lng,
        "radius": radius_km,
        "photos": "true",
        "geo": "true",
        "per_page": min(per_page, 200),
        "page": page,
        "order_by": "observed_on",
        "order": "desc",
    }
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(INAT_OBSERVATIONS_URL, params=params, headers={"User-Agent": "photo-opportunity-engine/0.1"})
        response.raise_for_status()
    return response.json()


def normalize_observation(item: dict[str, Any]) -> dict[str, Any] | None:
    location = item.get("geojson") or {}
    coords = location.get("coordinates") or []
    if len(coords) < 2 or not item.get("observed_on_details"):
        return None
    observed_at = item.get("time_observed_at") or item.get("observed_on")
    if not observed_at:
        return None
    taxon = item.get("taxon") or {}
    return {
        "source": "inaturalist",
        "source_photo_id": str(item.get("id")),
        "lat": float(coords[1]),
        "lng": float(coords[0]),
        "taken_at": observed_at,
        "views": None,
        "favorites": item.get("faves_count"),
        "owner_name": (item.get("user") or {}).get("login"),
        "tags": taxon.get("preferred_common_name") or taxon.get("name"),
        "payload": item,
    }
