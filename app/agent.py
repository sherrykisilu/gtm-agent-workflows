import json
from pathlib import Path
from typing import Protocol

from app.models import AccountBrief, Citation, WorkflowCreate


class BriefProvider(Protocol):
    async def generate(
        self, request: WorkflowCreate, citations: list[Citation]
    ) -> AccountBrief: ...


class ReplayBriefProvider:
    """Deterministic provider used by local demos, CI, and evaluation."""

    def __init__(self, replay_path: Path):
        self.replay_path = replay_path

    async def generate(
        self, request: WorkflowCreate, citations: list[Citation]
    ) -> AccountBrief:
        templates = json.loads(self.replay_path.read_text(encoding="utf-8"))
        template = templates["default"]
        event = request.account_event
        transcript = request.meeting_notes.transcript.lower()
        needs = [
            label
            for keyword, label in template["needs_by_keyword"].items()
            if keyword in transcript
        ] or [template["fallback_need"]]
        risks = [
            label
            for keyword, label in template["risks_by_keyword"].items()
            if keyword in transcript
        ] or [template["fallback_risk"]]
        evidence_note = (
            f"Grounded in {len(citations)} approved document(s)."
            if citations
            else "No approved knowledge matched; avoid product-specific claims."
        )
        return AccountBrief.model_validate(
            {
                "account_summary": (
                    f"{event.account_name} engaged through {event.source}. "
                    f"{event.contact_name} described a need for {needs[0].lower()} "
                    f"during meeting {request.meeting_notes.meeting_id}. {evidence_note}"
                ),
                "needs": needs,
                "risks": risks,
                "recommended_next_step": template["recommended_next_step"],
                "citations": [citation.model_dump() for citation in citations],
                "proposed_action": {
                    "channel": "email",
                    "recipient": event.contact_email,
                    "subject": f"Follow-up: {event.account_name} workflow discussion",
                    "body": (
                        f"Hi {event.contact_name},\n\n"
                        "Thank you for the conversation. Based on the notes, the next "
                        f"step is to {template['action_step']}. "
                        "This draft is pending human review and has not been sent.\n"
                    ),
                },
            }
        )

