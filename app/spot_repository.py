from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SPOTS_PATH = ROOT / "data" / "photo_spots.json"


def distance_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    radius = 6371000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lam = math.radians(lng2 - lng1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lam / 2) ** 2
    return 2 * radius * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_spots(lat: float, lng: float, radius_m: int) -> list[dict[str, Any]]:
    spots = json.loads(SPOTS_PATH.read_text(encoding="utf-8"))
    matched = []
    for spot in spots:
        distance = distance_m(lat, lng, spot["lat"], spot["lng"])
        if distance <= radius_m:
            item = dict(spot)
            item["distance_m"] = round(distance)
            matched.append(item)
    return sorted(matched, key=lambda item: item["distance_m"])
