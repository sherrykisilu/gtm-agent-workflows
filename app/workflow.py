import asyncio
from collections.abc import Awaitable, Callable

from app.adapters import AdapterRegistry
from app.agent import BriefProvider
from app.config import Settings
from app.database import WorkflowStore
from app.models import WorkflowState
from app.policy import evaluate_policy
from app.retrieval import LocalRetriever


class WorkflowEngine:
    def __init__(
        self,
        store: WorkflowStore,
        retriever: LocalRetriever,
        provider: BriefProvider,
        adapters: AdapterRegistry,
        settings: Settings,
    ):
        self.store = store
        self.retriever = retriever
        self.provider = provider
        self.adapters = adapters
        self.settings = settings
        self.tasks: set[asyncio.Task[None]] = set()

    def enqueue(self, workflow_id: str) -> None:
        task = asyncio.create_task(self.run(workflow_id))
        self.tasks.add(task)
        task.add_done_callback(self.tasks.discard)

    async def run(self, workflow_id: str) -> None:
        record = await self.store.get(workflow_id)
        if record is None:
            return
        await self.store.transition(
            workflow_id, WorkflowState.QUEUED, "Workflow queued for asynchronous processing"
        )
        for attempt in range(1, self.settings.max_attempts + 1):
            try:
                await self.store.transition(
                    workflow_id,
                    WorkflowState.RETRIEVING,
                    "Searching approved local knowledge",
                    increment_attempts=True,
                )
                query = (
                    f"{record.request.account_event.account_name} "
                    f"{record.request.meeting_notes.transcript}"
                )
                citations = self.retriever.search(query)
                await self.store.transition(
                    workflow_id,
                    WorkflowState.GENERATING,
                    "Calling deterministic structured-output provider",
                )
                brief = await self.provider.generate(record.request, citations)
                await self.store.transition(
                    workflow_id,
                    WorkflowState.POLICY_CHECK,
                    "Checking grounding, recipients, and unsupported claims",
                    result=brief,
                )
                approved_ids = {
                    document.document_id for document in self.retriever.load()
                }
                policy = evaluate_policy(record.request, brief, approved_ids)
                if not policy.passed:
                    await self.store.transition(
                        workflow_id,
                        WorkflowState.FAILED,
                        "Policy checks blocked the generated action",
                        policy=policy,
                        error="; ".join(policy.violations),
                    )
                    return
                await self.store.transition(
                    workflow_id,
                    WorkflowState.AWAITING_APPROVAL,
                    "Draft is ready; external action remains blocked pending approval",
                    policy=policy,
                )
                return
            except Exception as exc:
                if attempt >= self.settings.max_attempts:
                    await self.store.transition(
                        workflow_id,
                        WorkflowState.FAILED,
                        "Retry budget exhausted",
                        error=f"{type(exc).__name__}: {exc}",
                    )
                    return
                await self.store.transition(
                    workflow_id,
                    WorkflowState.RETRYING,
                    f"Attempt {attempt} failed; retrying with backoff",
                    error=f"{type(exc).__name__}: {exc}",
                )
                await asyncio.sleep(self.settings.retry_delay_seconds * attempt)

    async def execute_approved(self, workflow_id: str) -> None:
        record = await self.store.get(workflow_id)
        if record is None or record.result is None:
            raise KeyError(workflow_id)
        await self.store.transition(
            workflow_id,
            WorkflowState.EXECUTING,
            "Human approval recorded; executing through replay adapter",
        )
        try:
            external_id = await self.adapters.execute(
                record.request, record.result.proposed_action
            )
        except Exception as exc:
            await self.store.transition(
                workflow_id,
                WorkflowState.FAILED,
                "Approved action failed in adapter",
                error=f"{type(exc).__name__}: {exc}",
            )
            return
        await self.store.transition(
            workflow_id,
            WorkflowState.COMPLETED,
            f"Replay adapter completed action as {external_id}",
        )

    async def drain(self) -> None:
        if self.tasks:
            await asyncio.gather(*self.tasks)

