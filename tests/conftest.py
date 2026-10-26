import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import create_app


@pytest.fixture
def client(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GTM_DATABASE_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv(
        "GTM_KNOWLEDGE_PATH", str(Path("sample_data/knowledge").resolve())
    )
    monkeypatch.setenv(
        "GTM_REPLAY_PATH", str(Path("sample_data/replay_responses.json").resolve())
    )
    get_settings.cache_clear()
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client
    get_settings.cache_clear()


@pytest.fixture
def payload() -> dict:
    return {
        "account_event": {
            "event_type": "meeting_completed",
            "account_id": "acct-1",
            "account_name": "Northwind Labs",
            "contact_name": "Avery Morgan",
            "contact_email": "avery@example.test",
            "source": "pytest",
            "attributes": {},
        },
        "meeting_notes": {
            "meeting_id": "meeting-1",
            "transcript": (
                "We need an integration for manual follow-up, with security review "
                "and human approval before any message is sent."
            ),
            "occurred_at": "2026-10-26T14:00:00Z",
        },
    }


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {
        "Authorization": "Bearer local-demo-token",
        "Idempotency-Key": "pytest-event-001",
    }


def wait_for_state(client: TestClient, workflow_id: str, expected: str) -> dict:
    headers = {"Authorization": "Bearer local-demo-token"}
    for _ in range(100):
        response = client.get(f"/api/workflows/{workflow_id}", headers=headers)
        body = response.json()
        if body["state"] == expected:
            return body
        asyncio.run(asyncio.sleep(0.01))
    raise AssertionError(f"workflow did not reach {expected}: {body}")

