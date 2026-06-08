from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from .agent_runtime import AgentRuntimeError, run_photo_opportunity_agent
from .memory_store import MemoryStore
from .models import Location, OpportunityRequest
from .orchestrator import run_opportunity_pipeline


class OpportunityLoop:
    def __init__(self, store: MemoryStore | None = None) -> None:
        self.store = store or MemoryStore()
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self.last_run: dict[str, Any] | None = None

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    async def run_once(
        self,
        *,
        user_id: str,
        location: Location,
        radius_m: int = 3000,
        subject: str = "sunset_landscape",
        loop_type: str = "manual_opportunity_check",
        when: datetime | None = None,
    ) -> dict[str, Any]:
        run_id = f"loop_{uuid.uuid4().hex}"
        request = OpportunityRequest(
            location=location,
            time=when or datetime.now(timezone.utc),
            radius_m=radius_m,
            subject=subject,
        )
        try:
            response = await run_opportunity_pipeline(request)
            agent_decision = None
            agent_error = None
            if response.agent_decision_packet["status"] == "ready_for_agent":
                try:
                    agent_decision = await run_photo_opportunity_agent(response.agent_decision_packet)
                    status = "agent_decision_completed"
                except AgentRuntimeError as exc:
                    agent_error = str(exc)
                    status = "agent_runtime_blocked"
            else:
                status = response.agent_decision_packet["status"]
            record_id = f"opp_{uuid.uuid4().hex}"
            payload = response.model_dump(mode="json")
            payload["agent_decision"] = agent_decision
            payload["agent_error"] = agent_error
            self.store.insert_opportunity_record(
                record_id=record_id,
                user_id=user_id,
                run_id=run_id,
                status=status,
                score=response.score.score,
                payload=payload,
            )
            result = {
                "run_id": run_id,
                "loop_type": loop_type,
                "status": status,
                "record_id": record_id,
                "score": response.score.score,
                "failure_state": "agent_runtime_blocked" if agent_error else response.agent_decision_packet.get("failure_state"),
                "agent_decision": agent_decision,
                "agent_error": agent_error,
                "response": payload,
            }
            self.store.insert_loop_run(run_id, loop_type, status, result)
            self.last_run = result
            return result
        except Exception as exc:
            result = {
                "run_id": run_id,
                "loop_type": loop_type,
                "status": "failed",
                "failure_state": "loop_execution_failed",
                "error": str(exc),
            }
            self.store.insert_loop_run(run_id, loop_type, "failed", result)
            self.last_run = result
            return result

    async def start_15m(
        self,
        *,
        user_id: str,
        location: Location,
        radius_m: int = 3000,
        subject: str = "sunset_landscape",
        interval_seconds: int = 900,
    ) -> None:
        if self.running:
            return
        self._stop = asyncio.Event()
        self._task = asyncio.create_task(
            self._run_forever(
                user_id=user_id,
                location=location,
                radius_m=radius_m,
                subject=subject,
                interval_seconds=interval_seconds,
            )
        )

    async def stop(self) -> None:
        self._stop.set()
        if self._task:
            await self._task

    async def _run_forever(
        self,
        *,
        user_id: str,
        location: Location,
        radius_m: int,
        subject: str,
        interval_seconds: int,
    ) -> None:
        while not self._stop.is_set():
            await self.run_once(
                user_id=user_id,
                location=location,
                radius_m=radius_m,
                subject=subject,
                loop_type="nearby_15m_opportunity_check",
            )
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=interval_seconds)
            except asyncio.TimeoutError:
                continue

    async def daily_morning_digest(
        self,
        *,
        user_id: str,
        location: Location,
        radius_m: int = 3000,
        subject: str = "sunset_landscape",
    ) -> dict[str, Any]:
        now = datetime.now(timezone.utc)
        checks = []
        for hour_offset in (0, 3, 6, 9, 12):
            checks.append(
                await self.run_once(
                    user_id=user_id,
                    location=location,
                    radius_m=radius_m,
                    subject=subject,
                    loop_type="daily_morning_digest",
                    when=now + timedelta(hours=hour_offset),
                )
            )
        return {
            "status": "completed",
            "checks": checks,
            "best": max(checks, key=lambda item: item.get("score", 0)) if checks else None,
        }


loop = OpportunityLoop()
