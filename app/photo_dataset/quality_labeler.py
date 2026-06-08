from __future__ import annotations

from typing import Any


def commons_quality_label(item: dict[str, Any]) -> tuple[int, float, str, dict[str, Any]]:
    payload = item.get("payload") or {}
    width = payload.get("width") or 0
    height = payload.get("height") or 0
    megapixels = (width * height) / 1_000_000 if width and height else 0
    has_gps = item.get("lat") is not None and item.get("lng") is not None
    has_time = bool(item.get("taken_at"))
    score = min(1.0, megapixels / 12)
    if has_gps:
        score += 0.1
    if has_time:
        score += 0.1
    score = round(min(score, 1.0), 3)
    return int(score >= 0.55), score, "commons_metadata_quality_v1", {"megapixels": round(megapixels, 2), "has_gps": has_gps, "has_time": has_time}


def inaturalist_quality_label(item: dict[str, Any]) -> tuple[int, float, str, dict[str, Any]]:
    favorites = item.get("favorites") or 0
    payload = item.get("payload") or {}
    photo_count = len(payload.get("photos") or [])
    score = min(1.0, favorites / 20) * 0.5 + min(1.0, photo_count / 3) * 0.5
    score = round(score, 3)
    return int(score >= 0.5), score, "inaturalist_favorites_photo_count_v1", {"favorites": favorites, "photo_count": photo_count}
