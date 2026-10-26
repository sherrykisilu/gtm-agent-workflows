from app.models import AccountBrief, WorkflowCreate
from app.policy import evaluate_policy


def test_policy_rejects_unapproved_citation(payload: dict):
    request = WorkflowCreate.model_validate(payload)
    brief = AccountBrief.model_validate(
        {
            "account_summary": "A grounded summary.",
            "needs": ["Integration"],
            "risks": ["Timeline"],
            "recommended_next_step": "Review requirements.",
            "citations": [
                {
                    "document_id": "invented",
                    "title": "Invented",
                    "quote": "Not approved",
                }
            ],
            "proposed_action": {
                "channel": "email",
                "recipient": "avery@example.test",
                "subject": "Follow-up",
                "body": "Please review.",
            },
        }
    )
    result = evaluate_policy(request, brief, {"approved-capabilities"})
    assert result.passed is False
    assert "unapproved documents" in result.violations[0]

