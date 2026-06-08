from __future__ import annotations

import sqlite3
from typing import Any

from app.opportunity_database import DB_PATH


def condition_matches(features: dict[str, Any], condition: dict[str, Any]) -> bool:
    value = features.get(condition["field"])
    target = condition["value"]
    op = condition["op"]
    if value is None:
        return False
    if op == ">=":
        return value >= target
    if op == "<=":
        return value <= target
    if op == "==":
        return value == target
    raise ValueError(f"unsupported op: {op}")


def backtest_factor(factor: dict[str, Any]) -> dict[str, Any]:
    if not DB_PATH.exists():
        return empty_result(factor)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            rows = conn.execute(
                """
                select e.feature_json, q.quality_label
                from photo_context_enrichment e
                join photo_quality_labels q
                  on q.source = e.source and q.source_photo_id = e.source_photo_id
                where e.status = 'enriched' and e.feature_json is not null
                """
            ).fetchall()
        except sqlite3.OperationalError:
            return empty_result(factor)
    total = len(rows)
    if total == 0:
        return {**factor, "sample_size": 0, "hit_rate": 0.0, "lift": 0.0, "false_alert_rate": 0.0, "status": "candidate"}
    matches = 0
    positives = 0
    matched_positives = 0
    for feature_json, quality_label in rows:
        import json

        features = json.loads(feature_json)
        positive = int(quality_label) == 1
        positives += int(positive)
        matched = all(condition_matches(features, condition) for condition in factor.get("conditions", []))
        matches += int(matched)
        matched_positives += int(matched and positive)
    baseline = positives / total if total else 0
    hit_rate = matched_positives / matches if matches else 0
    lift = hit_rate / baseline if baseline else 0
    false_alert_rate = (matches - matched_positives) / matches if matches else 0
    status = "promising" if matches >= 10 and lift >= 1.2 else "candidate"
    return {
        **factor,
        "sample_size": total,
        "matches": matches,
        "hit_rate": round(hit_rate, 3),
        "lift": round(lift, 3),
        "false_alert_rate": round(false_alert_rate, 3),
        "status": status,
    }


def empty_result(factor: dict[str, Any]) -> dict[str, Any]:
    return {**factor, "sample_size": 0, "matches": 0, "hit_rate": 0.0, "lift": 0.0, "false_alert_rate": 0.0, "status": "candidate"}


def backtest_factors(factors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [backtest_factor(factor) for factor in factors]
