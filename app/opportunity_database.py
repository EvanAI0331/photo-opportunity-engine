from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "photo_opportunity.sqlite3"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class OpportunityDatabase:
    def __init__(self, path: Path = DB_PATH) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.init()

    def connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        return conn

    def init(self) -> None:
        with self.connect() as conn:
            conn.executescript(
                """
                create table if not exists photo_observations (
                  source text not null,
                  source_photo_id text not null,
                  lat real not null,
                  lng real not null,
                  taken_at text not null,
                  views integer,
                  favorites integer,
                  owner_name text,
                  tags text,
                  payload_json text not null,
                  created_at text not null,
                  primary key (source, source_photo_id)
                );
                create table if not exists osm_place_features (
                  place_key text not null,
                  osm_id text not null,
                  feature_type text not null,
                  lat real,
                  lng real,
                  name text,
                  payload_json text not null,
                  created_at text not null,
                  primary key (place_key, osm_id)
                );
                create table if not exists photo_context_enrichment (
                  source text not null,
                  source_photo_id text not null,
                  weather_json text,
                  astronomy_json text,
                  feature_json text,
                  status text not null,
                  failure_state text,
                  updated_at text not null,
                  primary key (source, source_photo_id)
                );
                create table if not exists photo_quality_labels (
                  source text not null,
                  source_photo_id text not null,
                  quality_label integer not null,
                  quality_score real not null,
                  label_source text not null,
                  payload_json text not null,
                  updated_at text not null,
                  primary key (source, source_photo_id)
                );
                create table if not exists spot_photo_samples (
                  spot_id text not null,
                  source text not null,
                  source_photo_id text not null,
                  distance_m real not null,
                  payload_json text not null,
                  created_at text not null,
                  primary key (spot_id, source, source_photo_id)
                );
                create table if not exists cold_start_runs (
                  run_id text primary key,
                  place_key text not null,
                  status text not null,
                  payload_json text not null,
                  created_at text not null
                );
                """
            )

    def upsert_photo_observation(self, item: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                insert into photo_observations
                (source, source_photo_id, lat, lng, taken_at, views, favorites, owner_name, tags, payload_json, created_at)
                values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(source, source_photo_id) do update set
                  lat=excluded.lat,
                  lng=excluded.lng,
                  taken_at=excluded.taken_at,
                  views=excluded.views,
                  favorites=excluded.favorites,
                  owner_name=excluded.owner_name,
                  tags=excluded.tags,
                  payload_json=excluded.payload_json
                """,
                (
                    item["source"],
                    item["source_photo_id"],
                    item["lat"],
                    item["lng"],
                    item["taken_at"],
                    item.get("views"),
                    item.get("favorites"),
                    item.get("owner_name"),
                    item.get("tags"),
                    json.dumps(item.get("payload", item), ensure_ascii=False),
                    now_iso(),
                ),
            )

    def upsert_context_enrichment(self, source: str, source_photo_id: str, status: str, weather: dict[str, Any] | None, astronomy: dict[str, Any] | None, features: dict[str, Any] | None, failure_state: str | None = None) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                insert into photo_context_enrichment
                (source, source_photo_id, weather_json, astronomy_json, feature_json, status, failure_state, updated_at)
                values (?, ?, ?, ?, ?, ?, ?, ?)
                on conflict(source, source_photo_id) do update set
                  weather_json=excluded.weather_json,
                  astronomy_json=excluded.astronomy_json,
                  feature_json=excluded.feature_json,
                  status=excluded.status,
                  failure_state=excluded.failure_state,
                  updated_at=excluded.updated_at
                """,
                (
                    source,
                    source_photo_id,
                    json.dumps(weather, ensure_ascii=False) if weather is not None else None,
                    json.dumps(astronomy, ensure_ascii=False) if astronomy is not None else None,
                    json.dumps(features, ensure_ascii=False) if features is not None else None,
                    status,
                    failure_state,
                    now_iso(),
                ),
            )

    def upsert_quality_label(self, source: str, source_photo_id: str, quality_label: int, quality_score: float, label_source: str, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                insert into photo_quality_labels
                (source, source_photo_id, quality_label, quality_score, label_source, payload_json, updated_at)
                values (?, ?, ?, ?, ?, ?, ?)
                on conflict(source, source_photo_id) do update set
                  quality_label=excluded.quality_label,
                  quality_score=excluded.quality_score,
                  label_source=excluded.label_source,
                  payload_json=excluded.payload_json,
                  updated_at=excluded.updated_at
                """,
                (source, source_photo_id, quality_label, quality_score, label_source, json.dumps(payload, ensure_ascii=False), now_iso()),
            )

    def insert_cold_start_run(self, run_id: str, place_key: str, status: str, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "insert into cold_start_runs (run_id, place_key, status, payload_json, created_at) values (?, ?, ?, ?, ?)",
                (run_id, place_key, status, json.dumps(payload, ensure_ascii=False), now_iso()),
            )

    def upsert_spot_photo_sample(self, spot_id: str, source: str, source_photo_id: str, distance_m: float, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                insert into spot_photo_samples
                (spot_id, source, source_photo_id, distance_m, payload_json, created_at)
                values (?, ?, ?, ?, ?, ?)
                on conflict(spot_id, source, source_photo_id) do update set
                  distance_m=excluded.distance_m,
                  payload_json=excluded.payload_json
                """,
                (spot_id, source, source_photo_id, distance_m, json.dumps(payload, ensure_ascii=False), now_iso()),
            )

    def stats(self) -> dict[str, int]:
        tables = ["photo_observations", "osm_place_features", "photo_context_enrichment", "photo_quality_labels", "spot_photo_samples", "cold_start_runs"]
        with self.connect() as conn:
            return {table: conn.execute(f"select count(*) from {table}").fetchone()[0] for table in tables}
