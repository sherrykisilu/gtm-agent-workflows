from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from app.models import ProposedAction, WorkflowCreate


class CRMAdapter(ABC):
    @abstractmethod
    async def enrich_account(self, account_id: str) -> dict[str, str]: ...

    @abstractmethod
    async def create_follow_up_task(self, action: ProposedAction) -> str: ...


class MeetingAdapter(ABC):
    @abstractmethod
    async def get_notes(self, meeting_id: str) -> str: ...


class MessagingAdapter(ABC):
    @abstractmethod
    async def send(self, action: ProposedAction) -> str: ...


@dataclass
class ReplayCRMAdapter(CRMAdapter):
    tasks: list[ProposedAction] = field(default_factory=list)

    async def enrich_account(self, account_id: str) -> dict[str, str]:
        return {
            "account_id": account_id,
            "segment": "mid-market",
            "owner": "Demo Account Executive",
        }

    async def create_follow_up_task(self, action: ProposedAction) -> str:
        self.tasks.append(action)
        return f"crm-task-{len(self.tasks)}"


@dataclass
class ReplayMeetingAdapter(MeetingAdapter):
    requests: list[str] = field(default_factory=list)

    async def get_notes(self, meeting_id: str) -> str:
        self.requests.append(meeting_id)
        return "Meeting notes are supplied in the authenticated workflow request."


@dataclass
class ReplayMessagingAdapter(MessagingAdapter):
    messages: list[ProposedAction] = field(default_factory=list)

    async def send(self, action: ProposedAction) -> str:
        self.messages.append(action)
        return f"message-{len(self.messages)}"


@dataclass
class AdapterRegistry:
    crm: CRMAdapter
    meetings: MeetingAdapter
    messaging: MessagingAdapter

    @classmethod
    def replay(cls) -> "AdapterRegistry":
        return cls(
            crm=ReplayCRMAdapter(),
            meetings=ReplayMeetingAdapter(),
            messaging=ReplayMessagingAdapter(),
        )

    async def execute(self, request: WorkflowCreate, action: ProposedAction) -> str:
        if action.channel == "email":
            return await self.messaging.send(action)
        return await self.crm.create_follow_up_task(action)

