import re

from app.models import AccountBrief, PolicyResult, WorkflowCreate

UNSUPPORTED_PATTERNS = [
    re.compile(r"\bguarantee(?:d|s)?\b", re.IGNORECASE),
    re.compile(r"\b100%\b"),
    re.compile(r"\bproduction customer\b", re.IGNORECASE),
]


def evaluate_policy(
    request: WorkflowCreate, brief: AccountBrief, approved_document_ids: set[str]
) -> PolicyResult:
    violations: list[str] = []
    combined = " ".join(
        [
            brief.account_summary,
            brief.recommended_next_step,
            brief.proposed_action.body,
        ]
    )
    for pattern in UNSUPPORTED_PATTERNS:
        if pattern.search(combined):
            violations.append(f"unsupported claim matched pattern: {pattern.pattern}")
    if brief.proposed_action.recipient != request.account_event.contact_email:
        violations.append("proposed recipient differs from authenticated event contact")
    invalid_citations = [
        citation.document_id
        for citation in brief.citations
        if citation.document_id not in approved_document_ids
    ]
    if invalid_citations:
        violations.append(
            f"citations reference unapproved documents: {', '.join(invalid_citations)}"
        )
    if not brief.citations:
        violations.append("at least one approved citation is required")
    return PolicyResult(passed=not violations, violations=violations)

