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


def source_allowed_for_subject(source: str, label_source: str, subject: str) -> bool:
    source_key = f"{source} {label_source}".lower()
    subject_key = subject.lower()
    if "user_photo" in source_key:
        return True
    if "inaturalist" in source_key:
        return any(token in subject_key for token in ("nature", "wildlife", "bird", "macro"))
    if "wikimedia" in source_key:
        return True
    return True


def backtest_factor(factor: dict[str, Any]) -> dict[str, Any]:
    if not DB_PATH.exists():
        return empty_result(factor)
    with sqlite3.connect(DB_PATH) as conn:
        try:
            rows = conn.execute(
                """
                select
                  e.spot_id,
                  e.source,
                  e.source_photo_id,
                  e.feature_json,
                  q.quality_label,
                  q.label_source
                from photo_spot_context_enrichment e
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
    source_breakdown: dict[str, dict[str, int]] = {}
    eligible_total = 0
    for _spot_id, source, _source_photo_id, feature_json, quality_label, label_source in rows:
        import json

        source_key = str(label_source or source)
        source_breakdown.setdefault(source_key, {"samples": 0, "eligible_samples": 0, "positives": 0, "matches": 0})
        source_breakdown[source_key]["samples"] += 1
        if not source_allowed_for_subject(str(source), str(label_source), str(factor.get("subject", ""))):
            continue
        source_breakdown[source_key]["eligible_samples"] += 1
        eligible_total += 1
        features = json.loads(feature_json)
        positive = int(quality_label) == 1
        positives += int(positive)
        source_breakdown[source_key]["positives"] += int(positive)
        matched = all(condition_matches(features, condition) for condition in factor.get("conditions", []))
        matches += int(matched)
        source_breakdown[source_key]["matches"] += int(matched)
        matched_positives += int(matched and positive)
    if eligible_total == 0:
        return {
            **factor,
            "sample_size": total,
            "eligible_sample_size": 0,
            "matches": 0,
            "hit_rate": 0.0,
            "lift": 0.0,
            "false_alert_rate": 0.0,
            "status": "candidate",
            "validation_unit": "spot_photo_sample",
            "source_breakdown": source_breakdown,
        }
    baseline = positives / eligible_total
    hit_rate = matched_positives / matches if matches else 0
    lift = hit_rate / baseline if baseline else 0
    false_alert_rate = (matches - matched_positives) / matches if matches else 0
    status = "promising" if matches >= 10 and lift >= 1.2 else "candidate"
    return {
        **factor,
        "sample_size": total,
        "eligible_sample_size": eligible_total,
        "matches": matches,
        "hit_rate": round(hit_rate, 3),
        "lift": round(lift, 3),
        "false_alert_rate": round(false_alert_rate, 3),
        "status": status,
        "validation_unit": "spot_photo_sample",
        "source_breakdown": source_breakdown,
    }


def empty_result(factor: dict[str, Any]) -> dict[str, Any]:
    return {**factor, "sample_size": 0, "matches": 0, "hit_rate": 0.0, "lift": 0.0, "false_alert_rate": 0.0, "status": "candidate"}


def backtest_factors(factors: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [backtest_factor(factor) for factor in factors]
