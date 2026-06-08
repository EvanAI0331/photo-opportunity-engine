from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import OpportunityScore


def direction_from_azimuth(degrees: float | None) -> str | None:
    if degrees is None:
        return None
    directions = [
        "north",
        "north-northeast",
        "northeast",
        "east-northeast",
        "east",
        "east-southeast",
        "southeast",
        "south-southeast",
        "south",
        "south-southwest",
        "southwest",
        "west-southwest",
        "west",
        "west-northwest",
        "northwest",
        "north-northwest",
    ]
    return directions[int((degrees + 11.25) // 22.5) % 16]


def in_window(when: datetime, start_iso: str | None, end_iso: str | None) -> bool:
    if not start_iso or not end_iso:
        return False
    start = datetime.fromisoformat(start_iso.replace("Z", "+00:00")).astimezone(when.tzinfo)
    end = datetime.fromisoformat(end_iso.replace("Z", "+00:00")).astimezone(when.tzinfo)
    return start <= when <= end


def build_features(weather: dict[str, Any] | None, astronomy: dict[str, Any] | None, geo: dict[str, Any] | None, spots: list[dict[str, Any]], when: datetime) -> dict[str, Any]:
    weather = weather or {}
    astronomy = astronomy or {}
    geo = geo or {}
    sun = astronomy.get("sun") or {}
    moon = astronomy.get("moon") or {}
    times = astronomy.get("times") or {}
    visibility_m = weather.get("visibility")
    cloud_cover = weather.get("cloud_cover")
    humidity = weather.get("relative_humidity_2m")
    precip = weather.get("precipitation_probability")
    wind = weather.get("wind_speed_10m")
    water_count = int(geo.get("water") or 0) + int(geo.get("coastline") or 0)
    return {
        "golden_hour": in_window(when, times.get("goldenHour"), times.get("sunset")) or in_window(when, times.get("sunrise"), times.get("goldenHourEnd")),
        "blue_hour": in_window(when, times.get("dusk"), times.get("night")) or in_window(when, times.get("nightEnd"), times.get("dawn")),
        "sun_azimuth": sun.get("azimuth"),
        "sun_direction": direction_from_azimuth(sun.get("azimuth")),
        "moon_azimuth": moon.get("azimuth"),
        "moon_direction": direction_from_azimuth(moon.get("azimuth")),
        "moon_phase": (astronomy.get("moon_illumination") or {}).get("phase"),
        "cloud_cover": cloud_cover,
        "visibility_km": round(visibility_m / 1000, 1) if isinstance(visibility_m, (int, float)) else None,
        "humidity": humidity,
        "precipitation_probability": precip,
        "wind_speed_10m": wind,
        "fog_probability": estimate_fog_probability(humidity, visibility_m, wind),
        "water_reflection_score": min(1.0, 0.35 + water_count * 0.2) if water_count else 0.0,
        "landmark_visibility_score": estimate_landmark_visibility(visibility_m, precip),
        "viewpoint_count": geo.get("viewpoints", 0),
        "bridge_count": geo.get("bridges", 0),
        "nearby_spot_count": len(spots),
    }


def estimate_fog_probability(humidity: Any, visibility_m: Any, wind: Any) -> float | None:
    if not isinstance(humidity, (int, float)) or not isinstance(visibility_m, (int, float)):
        return None
    score = 0.0
    if humidity >= 95:
        score += 0.45
    elif humidity >= 85:
        score += 0.25
    if visibility_m < 5000:
        score += 0.35
    if isinstance(wind, (int, float)) and wind <= 8:
        score += 0.15
    return round(min(score, 1.0), 2)


def estimate_landmark_visibility(visibility_m: Any, precip: Any) -> float | None:
    if not isinstance(visibility_m, (int, float)):
        return None
    score = min(1.0, visibility_m / 20000)
    if isinstance(precip, (int, float)):
        score -= min(0.4, precip / 250)
    return round(max(0.0, score), 2)


def score_opportunity(subject: str, when: datetime, features: dict[str, Any], astronomy: dict[str, Any] | None, spots: list[dict[str, Any]], missing_sources: list[str] | None = None) -> OpportunityScore:
    missing = list(missing_sources or [])
    for field in ("cloud_cover", "visibility_km", "precipitation_probability", "sun_azimuth"):
        if features.get(field) is None:
            missing.append(field)
    if missing:
        return OpportunityScore(
            opportunity_type=subject,
            score=0,
            status="insufficient_data",
            window=None,
            direction=features.get("sun_direction"),
            reason="missing required photographic evidence",
            evidence=[],
            penalties=[],
            missing_evidence=missing,
        )

    golden_hour = bool(features.get("golden_hour"))
    blue_hour = bool(features.get("blue_hour"))
    cloud = features["cloud_cover"]
    visibility = features["visibility_km"]
    precip = features["precipitation_probability"]
    reflection = features["water_reflection_score"]
    landmark = features["landmark_visibility_score"] or 0
    score = 0.0
    evidence = []
    penalties = []

    if golden_hour:
        score += 0.25
        evidence.append("golden hour window")
    elif blue_hour:
        score += 0.18
        evidence.append("blue hour window")

    if 35 <= cloud <= 75:
        score += 0.22
        evidence.append("cloud cover supports textured sky")
    elif cloud < 15 or cloud > 90:
        penalties.append("cloud cover is weak or overcast")
        score -= 0.08

    if visibility >= 12:
        score += 0.18
        evidence.append("visibility supports landmark clarity")
    else:
        penalties.append("visibility is limited")
        score -= 0.12

    if reflection:
        score += min(0.15, reflection * 0.15)
        evidence.append("nearby water supports reflection foreground")

    if landmark >= 0.65:
        score += 0.12
        evidence.append("landmark visibility is usable")

    if spots:
        score += 0.08
        evidence.append("known photo spot exists in radius")

    if precip >= 55:
        score -= 0.18
        penalties.append("rain probability is high")

    score = round(max(0.0, min(1.0, score)), 2)
    window = None
    if golden_hour:
        window = "golden_hour"
    elif blue_hour:
        window = "blue_hour"

    reason = " + ".join(evidence) if evidence else "weak photographic setup"
    return OpportunityScore(
        opportunity_type=subject,
        score=score,
        status="scored",
        window=window,
        direction=features.get("sun_direction"),
        reason=reason,
        evidence=evidence,
        penalties=penalties,
        missing_evidence=[],
    )
