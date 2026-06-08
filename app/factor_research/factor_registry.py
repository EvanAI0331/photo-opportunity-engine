from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = ROOT / "data" / "factor_registry.json"


def default_factors() -> list[dict[str, Any]]:
    return [
        {
            "factor_id": "sunset_high_cloud_clear_horizon_v1",
            "subject": "sunset_landscape",
            "conditions": [
                {"field": "high_cloud_cover", "op": ">=", "value": 35},
                {"field": "low_cloud_cover", "op": "<=", "value": 70},
                {"field": "visibility_km", "op": ">=", "value": 10},
                {"field": "direction_match_score", "op": ">=", "value": 0.7},
            ],
            "hit_rate": 0.0,
            "lift": 0.0,
            "false_alert_rate": 0.0,
            "status": "candidate",
        },
        {
            "factor_id": "blue_hour_known_spot_low_travel_v1",
            "subject": "sunset_landscape",
            "conditions": [
                {"field": "blue_hour", "op": "==", "value": True},
                {"field": "nearby_spot_count", "op": ">=", "value": 1},
                {"field": "travel_cost_score", "op": ">=", "value": 0.6},
            ],
            "hit_rate": 0.0,
            "lift": 0.0,
            "false_alert_rate": 0.0,
            "status": "candidate",
        },
    ]


def load_factors() -> list[dict[str, Any]]:
    if not REGISTRY_PATH.exists():
        save_factors(default_factors())
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def save_factors(factors: list[dict[str, Any]]) -> None:
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(json.dumps(factors, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
