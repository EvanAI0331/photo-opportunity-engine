from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx


COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"


async def category_files(category: str, limit: int = 50, cmcontinue: str | None = None) -> dict[str, Any]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "categorymembers",
        "gcmtitle": category if category.startswith("Category:") else f"Category:{category}",
        "gcmtype": "file",
        "gcmlimit": min(limit, 500),
        "prop": "imageinfo|coordinates",
        "iiprop": "url|mime|size|metadata|extmetadata|commonmetadata",
    }
    if cmcontinue:
        params["gcmcontinue"] = cmcontinue
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(COMMONS_API_URL, params=params, headers={"User-Agent": "photo-opportunity-engine/0.1"})
        response.raise_for_status()
    return response.json()


async def geosearch_files(lat: float, lng: float, radius_m: int = 1000, limit: int = 50, gscontinue: str | None = None) -> dict[str, Any]:
    params = {
        "action": "query",
        "format": "json",
        "generator": "geosearch",
        "ggscoord": f"{lat}|{lng}",
        "ggsradius": min(radius_m, 10000),
        "ggsnamespace": "6",
        "ggslimit": min(limit, 500),
        "prop": "imageinfo|coordinates",
        "iiprop": "url|mime|size|metadata|extmetadata|commonmetadata",
    }
    if gscontinue:
        params["ggscontinue"] = gscontinue
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(COMMONS_API_URL, params=params, headers={"User-Agent": "photo-opportunity-engine/0.1"})
        response.raise_for_status()
    return response.json()


def normalize_commons_page(page: dict[str, Any]) -> dict[str, Any] | None:
    imageinfo = (page.get("imageinfo") or [{}])[0]
    coords = page.get("coordinates") or []
    lat = coords[0].get("lat") if coords else None
    lng = coords[0].get("lon") if coords else None
    metadata = imageinfo.get("metadata") or []
    extmetadata = imageinfo.get("extmetadata") or {}
    taken_at = metadata_value(metadata, "DateTimeOriginal") or metadata_value(metadata, "DateTime") or ext_value(extmetadata, "DateTimeOriginal") or ext_value(extmetadata, "DateTime")
    if lat is None or lng is None or not taken_at:
        return None
    parsed_time = parse_commons_time(str(taken_at))
    if parsed_time is None:
        return None
    author = ext_value(extmetadata, "Artist") or ext_value(extmetadata, "Credit")
    return {
        "source": "wikimedia_commons",
        "source_photo_id": str(page.get("pageid")),
        "lat": float(lat),
        "lng": float(lng),
        "taken_at": parsed_time.isoformat(),
        "views": None,
        "favorites": None,
        "owner_name": strip_html(author) if author else None,
        "tags": page.get("title"),
        "payload": {
            "title": page.get("title"),
            "url": imageinfo.get("url"),
            "mime": imageinfo.get("mime"),
            "size": imageinfo.get("size"),
            "width": imageinfo.get("width"),
            "height": imageinfo.get("height"),
            "metadata": metadata,
            "extmetadata": extmetadata,
        },
    }


def metadata_value(metadata: list[dict[str, Any]], name: str) -> Any:
    for item in metadata:
        if item.get("name") == name:
            return item.get("value")
    return None


def ext_value(extmetadata: dict[str, Any], name: str) -> Any:
    value = extmetadata.get(name)
    return value.get("value") if isinstance(value, dict) else None


def parse_commons_time(value: str) -> datetime | None:
    candidates = [
        value.replace("Z", "+00:00"),
        value.replace(":", "-", 2),
    ]
    for candidate in candidates:
        try:
            parsed = datetime.fromisoformat(candidate)
            if parsed.tzinfo is None:
                return parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    return None


def strip_html(value: str) -> str:
    import re

    return re.sub(r"<[^>]+>", "", value).strip()
