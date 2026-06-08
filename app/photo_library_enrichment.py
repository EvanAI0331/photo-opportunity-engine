from __future__ import annotations

import asyncio
import json
import sqlite3
from datetime import datetime
from typing import Any

from .astronomy_connector import fetch_astronomy
from .historical_weather_connector import fetch_historical_weather
from .opportunity_database import DB_PATH, OpportunityDatabase
from .opportunity_engine import build_features


class PhotoLibraryEnrichmentWorker:
    def __init__(self) -> None:
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self.status: dict[str, Any] = {
            "running": False,
            "enriched": 0,
            "failed": 0,
            "last_error": None,
            "last_photo": None,
        }

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def start(self, *, batch_size: int = 50, sleep_seconds: float = 0.5, subject: str = "sunset_landscape") -> None:
        if self.running:
            return
        self._stop = asyncio.Event()
        self.status.update({"running": True, "batch_size": batch_size, "sleep_seconds": sleep_seconds, "subject": subject})
        self._task = asyncio.create_task(self._run(batch_size=batch_size, sleep_seconds=sleep_seconds, subject=subject))

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _run(self, *, batch_size: int, sleep_seconds: float, subject: str) -> None:
        try:
            while not self._stop.is_set():
                result = await enrich_batch(batch_size, subject)
                self.status["enriched"] += result["enriched"]
                self.status["failed"] += result["failed"]
                self.status["last_error"] = result["failures"][-1] if result["failures"] else None
                self.status["remaining"] = remaining_unenriched_count()
                if result["processed"] == 0 or self.status["remaining"] == 0:
                    break
                await asyncio.sleep(sleep_seconds)
        finally:
            self.status["running"] = False


def pending_rows(limit: int) -> list[sqlite3.Row]:
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        return conn.execute(
            """
            select o.source, o.source_photo_id, o.lat, o.lng, o.taken_at, s.payload_json as spot_payload
            from photo_observations o
            left join photo_context_enrichment e
              on e.source = o.source and e.source_photo_id = o.source_photo_id
            left join spot_photo_samples s
              on s.source = o.source and s.source_photo_id = o.source_photo_id
            where e.source_photo_id is null
            group by o.source, o.source_photo_id
            limit ?
            """,
            (limit,),
        ).fetchall()


def remaining_unenriched_count() -> int:
    with sqlite3.connect(DB_PATH) as conn:
        return conn.execute(
            """
            select count(*)
            from photo_observations o
            left join photo_context_enrichment e
              on e.source = o.source and e.source_photo_id = o.source_photo_id
            where e.source_photo_id is null
            """
        ).fetchone()[0]


async def enrich_batch(limit: int, subject: str = "sunset_landscape") -> dict[str, Any]:
    db = OpportunityDatabase()
    enriched = 0
    failed = 0
    failures = []
    rows = pending_rows(limit)
    for row in rows:
        try:
            when = datetime.fromisoformat(str(row["taken_at"]).replace("Z", "+00:00"))
            weather = await fetch_historical_weather(float(row["lat"]), float(row["lng"]), when)
            astronomy = await fetch_astronomy(float(row["lat"]), float(row["lng"]), when)
            spot_payload = json.loads(row["spot_payload"]) if row["spot_payload"] else {}
            spot = {
                "spot_id": spot_payload.get("spot_id"),
                "name": spot_payload.get("spot_name"),
                "lat": float(row["lat"]),
                "lng": float(row["lng"]),
                "best_directions_deg": [],
            }
            features = build_features(weather, astronomy, {}, [spot], when, subject)
            db.upsert_context_enrichment(row["source"], row["source_photo_id"], "enriched", weather, astronomy, features)
            enriched += 1
        except Exception as exc:
            db.upsert_context_enrichment(row["source"], row["source_photo_id"], "failed", None, None, None, "context_enrichment_failed")
            failure = {"source": row["source"], "source_photo_id": row["source_photo_id"], "error": str(exc)}
            failures.append(failure)
            failed += 1
    return {"processed": len(rows), "enriched": enriched, "failed": failed, "failures": failures[:20], "stats": db.stats()}


photo_library_enrichment_worker = PhotoLibraryEnrichmentWorker()
