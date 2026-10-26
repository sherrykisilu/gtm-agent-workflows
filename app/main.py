import json
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from app.adapters import AdapterRegistry
from app.agent import ReplayBriefProvider
from app.config import get_settings
from app.database import WorkflowStore
from app.models import (
    AdapterHealth,
    ApprovalRequest,
    HealthResponse,
    WebhookEnvelope,
    WorkflowCreate,
    WorkflowRecord,
    WorkflowState,
)
from app.retrieval import LocalRetriever
from app.security import require_api_token, verify_webhook
from app.workflow import WorkflowEngine


def create_app() -> FastAPI:
    settings = get_settings()
    store = WorkflowStore(settings.database_path)
    adapters = AdapterRegistry.replay()
    engine = WorkflowEngine(
        store=store,
        retriever=LocalRetriever(settings.knowledge_path),
        provider=ReplayBriefProvider(settings.replay_path),
        adapters=adapters,
        settings=settings,
    )

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await store.initialize()
        yield
        await engine.drain()

    app = FastAPI(
        title="GTM Approval Platform",
        version="0.1.0",
        description="Grounded account briefs with mandatory human approval.",
        lifespan=lifespan,
    )
    app.state.store = store
    app.state.engine = engine
    app.state.adapters = adapters
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.allowed_origins.split(",")],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            adapters=[
                AdapterHealth(name="crm", mode="replay", healthy=True),
                AdapterHealth(name="meeting", mode="replay", healthy=True),
                AdapterHealth(name="messaging", mode="replay", healthy=True),
            ],
        )

    @app.post(
        "/api/workflows",
        response_model=WorkflowRecord,
        status_code=status.HTTP_202_ACCEPTED,
        dependencies=[Depends(require_api_token)],
    )
    async def create_workflow(
        payload: WorkflowCreate,
        response: Response,
        idempotency_key: str = Header(alias="Idempotency-Key", min_length=8),
    ) -> WorkflowRecord:
        existing = await store.get_by_idempotency_key(idempotency_key)
        if existing:
            response.status_code = status.HTTP_200_OK
            return existing
        record = await store.create(str(uuid4()), idempotency_key, payload)
        engine.enqueue(record.id)
        return record

    @app.post(
        "/api/webhooks/inbound",
        response_model=WorkflowRecord,
        status_code=status.HTTP_202_ACCEPTED,
    )
    async def webhook(request: Request, response: Response) -> WorkflowRecord:
        body = await verify_webhook(request)
        envelope = WebhookEnvelope.model_validate(json.loads(body))
        existing = await store.get_by_idempotency_key(envelope.event_id)
        if existing:
            response.status_code = status.HTTP_200_OK
            return existing
        record = await store.create(
            str(uuid4()), envelope.event_id, envelope.payload
        )
        engine.enqueue(record.id)
        return record

    @app.get(
        "/api/workflows",
        response_model=list[WorkflowRecord],
        dependencies=[Depends(require_api_token)],
    )
    async def list_workflows() -> list[WorkflowRecord]:
        return await store.list()

    @app.get(
        "/api/workflows/{workflow_id}",
        response_model=WorkflowRecord,
        dependencies=[Depends(require_api_token)],
    )
    async def get_workflow(workflow_id: str) -> WorkflowRecord:
        record = await store.get(workflow_id)
        if record is None:
            raise HTTPException(status_code=404, detail="workflow not found")
        return record

    @app.post(
        "/api/workflows/{workflow_id}/decision",
        response_model=WorkflowRecord,
        dependencies=[Depends(require_api_token)],
    )
    async def decide(
        workflow_id: str, decision: ApprovalRequest
    ) -> WorkflowRecord:
        record = await store.get(workflow_id)
        if record is None:
            raise HTTPException(status_code=404, detail="workflow not found")
        if record.state != WorkflowState.AWAITING_APPROVAL:
            raise HTTPException(
                status_code=409,
                detail=f"decision is only valid from awaiting_approval, not {record.state}",
            )
        if decision.decision == "reject":
            return await store.transition(
                workflow_id,
                WorkflowState.REJECTED,
                f"Rejected by {decision.reviewer}: {decision.reason}",
            )
        await store.transition(
            workflow_id,
            WorkflowState.APPROVED,
            f"Approved by {decision.reviewer}: {decision.reason}",
        )
        await engine.execute_approved(workflow_id)
        approved = await store.get(workflow_id)
        if approved is None:
            raise HTTPException(status_code=404, detail="workflow not found")
        return approved

    return app


app = create_app()

