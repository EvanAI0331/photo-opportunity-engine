from __future__ import annotations

import uuid

from fastapi import FastAPI

from .memory_store import MemoryStore
from .models import FeedbackRequest, LoopRunRequest, LoopStartRequest, OpportunityRequest, OpportunityResponse, ShootingHistoryRequest
from .opportunity_database import OpportunityDatabase
from .photo_library_enrichment import photo_library_enrichment_worker, remaining_unenriched_count
from .agent_runtime import AgentRuntimeError, run_photo_opportunity_agent
from .opportunity_loop import loop
from .orchestrator import run_opportunity_pipeline


app = FastAPI(title="Photo Opportunity Engine", version="0.1.0")
store = MemoryStore()
opportunity_db = OpportunityDatabase()


@app.get("/health")
async def health():
    return {"ok": True}


@app.post("/opportunity", response_model=OpportunityResponse)
async def opportunity(request: OpportunityRequest):
    return await run_opportunity_pipeline(request, store=store)


@app.post("/agent/decide")
async def agent_decide(request: OpportunityRequest):
    response = await run_opportunity_pipeline(request, store=store)
    try:
        decision = await run_photo_opportunity_agent(response.agent_decision_packet)
        decision_status = decision.get("status")
        outer_status = "agent_decision_completed" if decision_status in {"notify", "skip", "passed"} else "agent_decision_blocked"
        return {
            "status": outer_status,
            "opportunity": response.model_dump(mode="json"),
            "agent_decision": decision,
            "failure_state": None if outer_status == "agent_decision_completed" else decision.get("failure_state", "agent_decision_blocked"),
        }
    except AgentRuntimeError as exc:
        return {
            "status": "blocked",
            "opportunity": response.model_dump(mode="json"),
            "agent_decision": None,
            "failure_state": "agent_runtime_blocked",
            "error": str(exc),
        }


@app.post("/loop/run-once")
async def loop_run_once(request: LoopRunRequest):
    return await loop.run_once(
        user_id=request.user_id,
        location=request.location,
        radius_m=request.radius_m,
        subject=request.subject,
    )


@app.post("/loop/start-15m")
async def loop_start_15m(request: LoopStartRequest):
    await loop.start_15m(
        user_id=request.user_id,
        location=request.location,
        radius_m=request.radius_m,
        subject=request.subject,
        interval_seconds=request.interval_seconds,
    )
    return {"ok": True, "running": loop.running, "interval_seconds": request.interval_seconds}


@app.post("/loop/stop")
async def loop_stop():
    await loop.stop()
    return {"ok": True, "running": loop.running}


@app.get("/loop/status")
async def loop_status():
    return {
        "running": loop.running,
        "last_run": loop.last_run,
        "recent_runs": store.latest_loop_runs(limit=10),
    }


@app.post("/loop/daily-morning")
async def loop_daily_morning(request: LoopRunRequest):
    return await loop.daily_morning_digest(
        user_id=request.user_id,
        location=request.location,
        radius_m=request.radius_m,
        subject=request.subject,
    )


@app.get("/memory/opportunities")
async def memory_opportunities(limit: int = 20):
    return {"items": store.latest_opportunities(limit=limit)}


@app.get("/opportunity-db/stats")
async def opportunity_db_stats():
    return {**opportunity_db.stats(), "remaining_unenriched": remaining_unenriched_count()}


@app.post("/photo-library/enrichment/start")
async def photo_library_enrichment_start(batch_size: int = 50, sleep_seconds: float = 0.5, subject: str = "sunset_landscape"):
    await photo_library_enrichment_worker.start(batch_size=batch_size, sleep_seconds=sleep_seconds, subject=subject)
    return {"ok": True, **photo_library_enrichment_worker.status}


@app.post("/photo-library/enrichment/stop")
async def photo_library_enrichment_stop():
    await photo_library_enrichment_worker.stop()
    return {"ok": True, **photo_library_enrichment_worker.status}


@app.get("/photo-library/enrichment/status")
async def photo_library_enrichment_status():
    return {**photo_library_enrichment_worker.status, "remaining_unenriched": remaining_unenriched_count()}


@app.post("/feedback")
async def feedback(request: FeedbackRequest):
    alert_id = request.alert_id or f"alert_{request.action}_{uuid.uuid4().hex}"
    table = "accepted_alerts" if request.action == "accepted" else "ignored_alerts"
    store.insert_event(table, "alert_id", alert_id, request.user_id, request.payload)
    return {"ok": True, "table": table, "alert_id": alert_id}


@app.post("/shooting-history")
async def shooting_history(request: ShootingHistoryRequest):
    shoot_id = request.payload.get("shoot_id") or f"shoot_{uuid.uuid4().hex}"
    store.insert_event("shooting_history", "shoot_id", shoot_id, request.user_id, request.payload)
    return {"ok": True, "shoot_id": shoot_id}
