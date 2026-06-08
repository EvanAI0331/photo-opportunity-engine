from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data" / "photo_memory.sqlite3"


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class MemoryStore:
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
                create table if not exists user_profile (
                  user_id text primary key,
                  payload_json text not null,
                  updated_at text not null
                );
                create table if not exists photo_preferences (
                  user_id text primary key,
                  payload_json text not null,
                  updated_at text not null
                );
                create table if not exists ignored_alerts (
                  alert_id text primary key,
                  user_id text not null,
                  payload_json text not null,
                  created_at text not null
                );
                create table if not exists accepted_alerts (
                  alert_id text primary key,
                  user_id text not null,
                  payload_json text not null,
                  created_at text not null
                );
                create table if not exists shooting_history (
                  shoot_id text primary key,
                  user_id text not null,
                  payload_json text not null,
                  created_at text not null
                );
                create table if not exists location_favorites (
                  favorite_id text primary key,
                  user_id text not null,
                  payload_json text not null,
                  created_at text not null
                );
                create table if not exists lens_preferences (
                  user_id text primary key,
                  payload_json text not null,
                  updated_at text not null
                );
                create table if not exists project_goals (
                  goal_id text primary key,
                  user_id text not null,
                  payload_json text not null,
                  created_at text not null
                );
                create table if not exists loop_runs (
                  run_id text primary key,
                  loop_type text not null,
                  status text not null,
                  payload_json text not null,
                  created_at text not null
                );
                create table if not exists opportunity_records (
                  record_id text primary key,
                  user_id text not null,
                  run_id text,
                  status text not null,
                  score real not null,
                  payload_json text not null,
                  created_at text not null
                );
                """
            )

    def upsert_profile(self, user_id: str, payload: dict[str, Any]) -> None:
        self._upsert_single("user_profile", "user_id", user_id, payload)

    def upsert_photo_preferences(self, user_id: str, payload: dict[str, Any]) -> None:
        self._upsert_single("photo_preferences", "user_id", user_id, payload)

    def upsert_lens_preferences(self, user_id: str, payload: dict[str, Any]) -> None:
        self._upsert_single("lens_preferences", "user_id", user_id, payload)

    def _upsert_single(self, table: str, key: str, value: str, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                f"""
                insert into {table} ({key}, payload_json, updated_at)
                values (?, ?, ?)
                on conflict({key}) do update set payload_json=excluded.payload_json, updated_at=excluded.updated_at
                """,
                (value, json.dumps(payload, ensure_ascii=False), now_iso()),
            )

    def insert_event(self, table: str, id_field: str, event_id: str, user_id: str, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                f"insert into {table} ({id_field}, user_id, payload_json, created_at) values (?, ?, ?, ?)",
                (event_id, user_id, json.dumps(payload, ensure_ascii=False), now_iso()),
            )

    def insert_loop_run(self, run_id: str, loop_type: str, status: str, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                "insert into loop_runs (run_id, loop_type, status, payload_json, created_at) values (?, ?, ?, ?, ?)",
                (run_id, loop_type, status, json.dumps(payload, ensure_ascii=False), now_iso()),
            )

    def insert_opportunity_record(self, record_id: str, user_id: str, run_id: str | None, status: str, score: float, payload: dict[str, Any]) -> None:
        with self.connect() as conn:
            conn.execute(
                """
                insert into opportunity_records (record_id, user_id, run_id, status, score, payload_json, created_at)
                values (?, ?, ?, ?, ?, ?, ?)
                """,
                (record_id, user_id, run_id, status, score, json.dumps(payload, ensure_ascii=False), now_iso()),
            )

    def latest_loop_runs(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "select * from loop_runs order by created_at desc limit ?",
                (limit,),
            ).fetchall()
        return [self._decode(row) for row in rows]

    def latest_opportunities(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as conn:
            rows = conn.execute(
                "select * from opportunity_records order by created_at desc limit ?",
                (limit,),
            ).fetchall()
        return [self._decode(row) for row in rows]

    @staticmethod
    def _decode(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        if "payload_json" in item:
            item["payload"] = json.loads(item.pop("payload_json"))
        return item
