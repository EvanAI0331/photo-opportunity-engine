from __future__ import annotations

from datetime import date
from typing import Any

import httpx

from .config import get_flickr_settings


FLICKR_REST_URL = "https://www.flickr.com/services/rest/"
SEARCH_EXTRAS = "date_taken,geo,views,tags,owner_name,url_s"


class FlickrConnectorError(RuntimeError):
    pass


async def search_geotagged_photos(
    *,
    lat: float,
    lng: float,
    radius_km: float,
    min_taken_date: date,
    max_taken_date: date,
    page: int = 1,
    per_page: int = 250,
    text: str | None = None,
) -> dict[str, Any]:
    settings = get_flickr_settings()
    if not settings.api_key:
        raise FlickrConnectorError("FLICKR_API_KEY is not configured")
    params: dict[str, Any] = {
        "method": "flickr.photos.search",
        "api_key": settings.api_key,
        "format": "json",
        "nojsoncallback": "1",
        "has_geo": "1",
        "lat": lat,
        "lon": lng,
        "radius": radius_km,
        "radius_units": "km",
        "min_taken_date": min_taken_date.isoformat(),
        "max_taken_date": max_taken_date.isoformat(),
        "extras": SEARCH_EXTRAS,
        "per_page": min(per_page, 500),
        "page": page,
        "media": "photos",
        "safe_search": "1",
    }
    if text:
        params["text"] = text
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(FLICKR_REST_URL, params=params)
        response.raise_for_status()
    payload = response.json()
    if payload.get("stat") != "ok":
        raise FlickrConnectorError(str(payload))
    return payload["photos"]
