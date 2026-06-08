from __future__ import annotations

from datetime import datetime
from typing import Any

from .models import OpportunityScore


def angular_distance(a: float, b: float) -> float:
    return abs((a - b + 180) % 360 - 180)


def direction_to_azimuth(direction: str | None) -> float | None:
    if not direction:
        return None
    mapping = {
        "north": 0,
        "north-northeast": 22.5,
        "northeast": 45,
        "east-northeast": 67.5,
        "east": 90,
        "east-southeast": 112.5,
        "southeast": 135,
        "south-southeast": 157.5,
        "south": 180,
        "south-southwest": 202.5,
        "southwest": 225,
        "west-southwest": 247.5,
        "west": 270,
        "west-northwest": 292.5,
        "northwest": 315,
        "north-northwest": 337.5,
    }
    return mapping.get(direction.lower())


def direction_match_score(sun_azimuth: Any, spots: list[dict[str, Any]]) -> float:
    if not isinstance(sun_azimuth, (int, float)) or not spots:
        return 0.0
    best = 0.0
    for spot in spots:
        targets = spot.get("best_directions_deg")
        if not isinstance(targets, list):
            legacy_target = direction_to_azimuth(spot.get("best_direction"))
            targets = [legacy_target] if legacy_target is not None else []
        for target in targets:
            if not isinstance(target, (int, float)):
                continue
            best = max(best, max(0.0, 1.0 - angular_distance(float(sun_azimuth), float(target)) / 90.0))
    return round(best, 2)


def spot_subject_match_score(subject: str, spots: list[dict[str, Any]]) -> float:
    if not spots:
        return 0.0
    tokens = set(subject.lower().replace("_", " ").split())
    best = 0.0
    for spot in spots:
        text = " ".join(spot.get("subjects", []) + spot.get("best_time", [])).lower()
        best = max(best, sum(1 for token in tokens if token in text) / max(len(tokens), 1))
    return round(min(best, 1.0), 2)


def travel_cost_score(spots: list[dict[str, Any]]) -> float:
    if not spots:
        return 0.0
    distance = min(float(spot.get("distance_m", 999999)) for spot in spots)
    if distance <= 500:
        return 1.0
    if distance >= 3000:
        return 0.0
    return round(1.0 - ((distance - 500) / 2500), 2)


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


def minutes_until(when: datetime, target_iso: str | None) -> int | None:
    if not target_iso:
        return None
    target = datetime.fromisoformat(target_iso.replace("Z", "+00:00")).astimezone(when.tzinfo)
    return round((target - when).total_seconds() / 60)


def build_features(weather: dict[str, Any] | None, astronomy: dict[str, Any] | None, geo: dict[str, Any] | None, spots: list[dict[str, Any]], when: datetime, subject: str = "sunset_landscape") -> dict[str, Any]:
    weather = weather or {}
    astronomy = astronomy or {}
    geo = geo or {}
    sun = astronomy.get("sun") or {}
    moon = astronomy.get("moon") or {}
    times = astronomy.get("times") or {}
    visibility_m = weather.get("visibility")
    cloud_cover = weather.get("cloud_cover")
    cloud_low = weather.get("cloud_cover_low")
    cloud_mid = weather.get("cloud_cover_mid")
    cloud_high = weather.get("cloud_cover_high")
    humidity = weather.get("relative_humidity_2m")
    precip = weather.get("precipitation_probability")
    wind = weather.get("wind_speed_10m")
    water_count = int(geo.get("water") or 0) + int(geo.get("coastline") or 0)
    return {
        "golden_hour": in_window(when, times.get("goldenHour"), times.get("sunset")) or in_window(when, times.get("sunrise"), times.get("goldenHourEnd")),
        "blue_hour": in_window(when, times.get("dusk"), times.get("night")) or in_window(when, times.get("nightEnd"), times.get("dawn")),
        "sun_azimuth": sun.get("azimuth"),
        "sun_altitude": sun.get("altitude"),
        "sun_direction": direction_from_azimuth(sun.get("azimuth")),
        "moon_azimuth": moon.get("azimuth"),
        "moon_direction": direction_from_azimuth(moon.get("azimuth")),
        "moon_phase": (astronomy.get("moon_illumination") or {}).get("phase"),
        "cloud_cover": cloud_cover,
        "low_cloud_cover": cloud_low,
        "mid_cloud_cover": cloud_mid,
        "high_cloud_cover": cloud_high,
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
        "direction_match_score": direction_match_score(sun.get("azimuth"), spots),
        "spot_subject_match_score": spot_subject_match_score(subject, spots),
        "travel_cost_score": travel_cost_score(spots),
        "time_to_sunset_minutes": minutes_until(when, times.get("sunset")),
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
    direction_match = features.get("direction_match_score") or 0
    subject_match = features.get("spot_subject_match_score") or 0
    travel = features.get("travel_cost_score") or 0
    high_cloud = features.get("high_cloud_cover")
    low_cloud = features.get("low_cloud_cover")
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

    if isinstance(high_cloud, (int, float)) and high_cloud >= 35:
        score += 0.08
        evidence.append("high cloud supports sunset color")
    if isinstance(low_cloud, (int, float)) and low_cloud >= 80:
        score -= 0.12
        penalties.append("low cloud may block horizon light")

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
    if direction_match >= 0.7:
        score += 0.14
        evidence.append("spot direction matches sun direction")
    elif spots:
        score -= 0.06
        penalties.append("spot direction does not match sun direction")
    if subject_match >= 0.5:
        score += 0.06
        evidence.append("spot subjects match requested subject")
    if travel >= 0.6:
        score += 0.04
        evidence.append("nearby spot has low travel cost")

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
