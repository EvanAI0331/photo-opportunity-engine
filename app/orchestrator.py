from __future__ import annotations

from typing import Any

from .astronomy_connector import fetch_astronomy
from .geo_connector import fetch_geo
from .models import ConnectorResult, OpportunityRequest, OpportunityResponse
from .opportunity_engine import build_features, score_opportunity
from .spot_repository import load_spots
from .weather_connector import fetch_weather


async def safe_connector(source: str, call) -> ConnectorResult:
    try:
        return ConnectorResult(source=source, ok=True, data=await call())
    except Exception as exc:
        return ConnectorResult(source=source, ok=False, error=str(exc))


async def run_opportunity_pipeline(request: OpportunityRequest) -> OpportunityResponse:
    lat = request.location.lat
    lng = request.location.lng
    weather = await safe_connector("open-meteo", lambda: fetch_weather(lat, lng, request.time))
    astronomy = await safe_connector("suncalc", lambda: fetch_astronomy(lat, lng, request.time))
    geo = await safe_connector("overpass", lambda: fetch_geo(lat, lng, request.radius_m))

    try:
        spots_data = load_spots(lat, lng, request.radius_m)
        spots = ConnectorResult(source="local-photo-spot-repository", ok=True, data=spots_data)
    except Exception as exc:
        spots_data = []
        spots = ConnectorResult(source="local-photo-spot-repository", ok=False, error=str(exc))

    weather_data = weather.data if weather.ok and isinstance(weather.data, dict) else None
    astronomy_data = astronomy.data if astronomy.ok and isinstance(astronomy.data, dict) else None
    geo_data = geo.data if geo.ok and isinstance(geo.data, dict) else None
    features = build_features(weather_data, astronomy_data, geo_data, spots_data, request.time)
    missing_sources = []
    if not weather.ok:
        missing_sources.append("weather_tool")
    if not astronomy.ok:
        missing_sources.append("astronomy_tool")
    if not geo.ok:
        missing_sources.append("geo_visibility_tool")
    if not spots.ok:
        missing_sources.append("photo_spot_tool")
    score = score_opportunity(request.subject, request.time, features, astronomy_data, spots_data, missing_sources)
    agent_decision_packet: dict[str, Any] = {
        "contract_id": "photo-opportunity-agent-v0-1",
        "status": "ready_for_agent" if score.status == "scored" else "blocked_before_agent",
        "normalized_location_time_radius_subject": request.model_dump(mode="json"),
        "photographic_feature_packet": features,
        "opportunity_score_packet": score.model_dump(),
        "candidate_photo_spots": spots_data[:5],
        "tool_call_trace": {
            "weather_tool": weather.ok,
            "astronomy_tool": astronomy.ok,
            "geo_visibility_tool": geo.ok,
            "photo_spot_tool": spots.ok,
        },
        "missing_evidence": score.missing_evidence,
        "failure_state": "blocked_missing_required_evidence" if score.status != "scored" else None,
    }
    return OpportunityResponse(
        context=request,
        weather=weather,
        astronomy=astronomy,
        geo=geo,
        spots=spots,
        photographic_features=features,
        score=score,
        agent_decision_packet=agent_decision_packet,
    )
