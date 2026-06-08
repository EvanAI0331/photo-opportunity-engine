from __future__ import annotations

import json
from typing import Any

import httpx

from .config import get_agent_settings
from .models import AgentDecision


SYSTEM_PROMPT = """You are photo_opportunity_decision_agent.
You are an LLM-backed photography opportunity decision agent governed by SpecX contract photo-opportunity-agent-v0-1.
Decide notify, skip, or blocked from the supplied evidence packet only.
Do not invent weather, location, spot, user preference, or notification evidence.
Use normalized_local_time and timezone from the evidence packet when discussing time. Do not infer or restate local time if those fields are absent.
Evidence summary must be a JSON array of concise evidence strings, not a free-form paragraph.
Return strict JSON with:
status, opportunity_type, score_used, confidence, recommended_window, recommended_spot, direction, subject, lens_or_focal_length, message, notify_lead_minutes, evidence_summary, penalties, missing_evidence, failure_state.
If required evidence is missing, status must be blocked and failure_state must be explicit.
"""


class AgentRuntimeError(RuntimeError):
    pass


async def run_photo_opportunity_agent(agent_packet: dict[str, Any]) -> dict[str, Any]:
    settings = get_agent_settings()
    if not settings.api_key:
        raise AgentRuntimeError("MINIMAX_API_KEY is not configured")

    payload = {
        "model": settings.model,
        "thinking": {"type": settings.thinking_type},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": "Decide the photography notification from this SpecX-governed evidence packet:\n"
                + json.dumps(agent_packet, ensure_ascii=False),
            },
        ],
        "temperature": settings.temperature,
        "max_completion_tokens": settings.max_completion_tokens,
    }
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.post(
            f"{settings.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {settings.api_key}",
                "Content-Type": "application/json",
            },
            json=payload,
        )
        response.raise_for_status()
    data = response.json()
    content = (((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "").strip()
    if content.startswith("```"):
        content = content.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        decision = json.loads(content)
    except json.JSONDecodeError as exc:
        raise AgentRuntimeError(f"Agent returned non-JSON content: {exc}") from exc
    if not isinstance(decision, dict):
        raise AgentRuntimeError("Agent decision is not a JSON object")
    if isinstance(decision.get("evidence_summary"), str):
        decision["evidence_summary"] = [decision["evidence_summary"]]
    if decision.get("status") not in {"notify", "skip", "blocked", "passed"}:
        raise AgentRuntimeError(f"Agent returned invalid status: {decision.get('status')}")
    decision["llm_provider"] = "minimax"
    decision["llm_model"] = settings.model
    decision["thinking_type"] = settings.thinking_type
    try:
        validated = AgentDecision.model_validate(decision).model_dump()
    except Exception as exc:
        raise AgentRuntimeError(f"Agent decision schema validation failed: {exc}") from exc
    expected_score = ((agent_packet.get("opportunity_score_packet") or {}).get("score"))
    if isinstance(expected_score, (int, float)) and abs(float(validated["score_used"]) - float(expected_score)) > 0.001:
        raise AgentRuntimeError(
            f"Agent decision score_used {validated['score_used']} does not match opportunity_score_packet.score {expected_score}"
        )
    return validated
