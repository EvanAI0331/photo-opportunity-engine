from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator

from .time_utils import ensure_timezone_aware


class Location(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)


class OpportunityRequest(BaseModel):
    location: Location
    time: datetime
    radius_m: int = Field(default=3000, ge=100, le=50000)
    subject: str = Field(default="sunset_landscape", min_length=1)

    @field_validator("time")
    @classmethod
    def time_must_be_aware(cls, value: datetime) -> datetime:
        return ensure_timezone_aware(value)


class ConnectorResult(BaseModel):
    source: str
    ok: bool
    data: dict[str, Any] | list[Any] | None = None
    error: str | None = None


class OpportunityScore(BaseModel):
    opportunity_type: str
    score: float = Field(ge=0, le=1)
    status: Literal["scored", "insufficient_data"]
    window: str | None
    direction: str | None
    reason: str
    evidence: list[str]
    penalties: list[str]
    missing_evidence: list[str]


class OpportunityResponse(BaseModel):
    context: OpportunityRequest
    weather: ConnectorResult
    astronomy: ConnectorResult
    geo: ConnectorResult
    spots: ConnectorResult
    photographic_features: dict[str, Any]
    score: OpportunityScore
    agent_decision_packet: dict[str, Any]


class AgentDecision(BaseModel):
    status: Literal["notify", "skip", "blocked", "passed"]
    opportunity_type: str | None = None
    score_used: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    recommended_window: str | None = None
    recommended_spot: str | None = None
    direction: str | None = None
    subject: str | None = None
    lens_or_focal_length: str | list[str] | None = None
    message: str = Field(min_length=1)
    notify_lead_minutes: int | None = Field(default=None, ge=0)
    evidence_summary: list[str] = Field(default_factory=list)
    penalties: list[str] = Field(default_factory=list)
    missing_evidence: list[str] = Field(default_factory=list)
    failure_state: str | None = None
    llm_provider: str | None = None
    llm_model: str | None = None
    thinking_type: str | None = None

    @field_validator("failure_state")
    @classmethod
    def blocked_requires_failure_state(cls, value: str | None, info):
        if info.data.get("status") == "blocked" and not value:
            raise ValueError("blocked decision requires failure_state")
        return value


class LoopRunRequest(BaseModel):
    user_id: str = Field(default="default")
    location: Location
    radius_m: int = Field(default=3000, ge=100, le=50000)
    subject: str = Field(default="sunset_landscape", min_length=1)


class LoopStartRequest(LoopRunRequest):
    interval_seconds: int = Field(default=900, ge=60, le=86400)


class FeedbackRequest(BaseModel):
    user_id: str = Field(default="default")
    alert_id: str | None = None
    action: Literal["accepted", "ignored"]
    payload: dict[str, Any] = Field(default_factory=dict)


class ShootingHistoryRequest(BaseModel):
    user_id: str = Field(default="default")
    payload: dict[str, Any] = Field(default_factory=dict)
