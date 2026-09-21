from typing import Any

from pydantic import BaseModel


class DataFreshnessMetadata(BaseModel):
    status: str
    data_timestamp: str | None = None
    checked_at: str
    source: str | None = None
    offline_cacheable: bool = True
    valid_until: str | None = None


class ResponseSegment(BaseModel):
    id: str
    text: str
    agents: list[str] = []


class AgentExecutionRecord(BaseModel):
    agent: str
    status: str
    reason_called: str
    inputs_used: dict[str, Any] = {}
    outputs: dict[str, Any] = {}
    output_reason: str
    sources: list[str] = []
    confidence: float
    score_source: str | None = None
    score_reason: str | None = None
    used_by: list[str] = []

class AgentExecutionAudit(BaseModel):
    execution_order: list[str]
    agents_called: list[AgentExecutionRecord]

class OrcaQueryResponse(BaseModel):
    query: str
    action: str
    response: str | None
    session_id: str | None = None
    segments: list[ResponseSegment] | None = None
    plan: dict[str, Any] | None
    extraction: dict[str, Any]
    execution: dict[str, Any] | None
    agent_execution: AgentExecutionAudit | None = None
    route_timings: dict[str, float]
    total_latency_ms: float
    data_freshness: DataFreshnessMetadata | None = None
