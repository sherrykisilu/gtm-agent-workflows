from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkflowState(StrEnum):
    RECEIVED = "received"
    QUEUED = "queued"
    RETRIEVING = "retrieving"
    GENERATING = "generating"
    POLICY_CHECK = "policy_check"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXECUTING = "executing"
    COMPLETED = "completed"
    RETRYING = "retrying"
    FAILED = "failed"


TERMINAL_STATES = {
    WorkflowState.COMPLETED,
    WorkflowState.REJECTED,
    WorkflowState.FAILED,
}


class AccountEvent(BaseModel):
    event_type: Literal["inbound_lead", "product_interest", "meeting_completed"]
    account_id: str = Field(min_length=1, max_length=100)
    account_name: str = Field(min_length=1, max_length=200)
    contact_name: str = Field(min_length=1, max_length=200)
    contact_email: str
    source: str = Field(default="demo", max_length=100)
    attributes: dict[str, Any] = Field(default_factory=dict)


class MeetingNotes(BaseModel):
    meeting_id: str = Field(min_length=1, max_length=100)
    transcript: str = Field(min_length=10, max_length=20_000)
    occurred_at: datetime


class WorkflowCreate(BaseModel):
    account_event: AccountEvent
    meeting_notes: MeetingNotes


class Citation(BaseModel):
    document_id: str
    title: str
    quote: str


class ProposedAction(BaseModel):
    channel: Literal["email", "crm_task"]
    recipient: str
    subject: str
    body: str


class AccountBrief(BaseModel):
    account_summary: str
    needs: list[str]
    risks: list[str]
    recommended_next_step: str
    citations: list[Citation]
    proposed_action: ProposedAction


class PolicyResult(BaseModel):
    passed: bool
    violations: list[str] = Field(default_factory=list)


class WorkflowEvent(BaseModel):
    state: WorkflowState
    at: datetime
    detail: str


class WorkflowRecord(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    idempotency_key: str
    state: WorkflowState
    request: WorkflowCreate
    result: AccountBrief | None = None
    policy: PolicyResult | None = None
    error: str | None = None
    attempts: int
    created_at: datetime
    updated_at: datetime
    events: list[WorkflowEvent] = Field(default_factory=list)


class ApprovalRequest(BaseModel):
    decision: Literal["approve", "reject"]
    reviewer: str = Field(min_length=2, max_length=100)
    reason: str = Field(min_length=2, max_length=1000)


class WebhookEnvelope(BaseModel):
    event_id: str = Field(min_length=1, max_length=100)
    payload: WorkflowCreate


class AdapterHealth(BaseModel):
    name: str
    mode: str
    healthy: bool


class HealthResponse(BaseModel):
    status: Literal["ok"]
    adapters: list[AdapterHealth]

