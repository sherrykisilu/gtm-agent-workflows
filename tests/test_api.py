import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from tests.conftest import wait_for_state


def test_workflow_requires_authentication(client: TestClient, payload: dict):
    response = client.post(
        "/api/workflows",
        json=payload,
        headers={"Idempotency-Key": "unauthorized-event"},
    )
    assert response.status_code == 401


def test_end_to_end_workflow_requires_approval(
    client: TestClient, payload: dict, auth_headers: dict[str, str]
):
    created = client.post("/api/workflows", json=payload, headers=auth_headers)
    assert created.status_code == 202
    workflow_id = created.json()["id"]

    pending = wait_for_state(client, workflow_id, "awaiting_approval")
    assert pending["policy"]["passed"] is True
    assert pending["result"]["citations"]

    decision = client.post(
        f"/api/workflows/{workflow_id}/decision",
        headers={"Authorization": "Bearer local-demo-token"},
        json={
            "decision": "approve",
            "reviewer": "Portfolio Reviewer",
            "reason": "Evidence and recipient verified",
        },
    )
    assert decision.status_code == 200
    assert decision.json()["state"] == "completed"
    states = [event["state"] for event in decision.json()["events"]]
    assert states.index("approved") < states.index("executing") < states.index("completed")


def test_idempotent_create_returns_existing_workflow(
    client: TestClient, payload: dict, auth_headers: dict[str, str]
):
    first = client.post("/api/workflows", json=payload, headers=auth_headers)
    second = client.post("/api/workflows", json=payload, headers=auth_headers)
    assert first.status_code == 202
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]


def test_cannot_bypass_approval(
    client: TestClient, payload: dict, auth_headers: dict[str, str]
):
    created = client.post("/api/workflows", json=payload, headers=auth_headers)
    workflow_id = created.json()["id"]
    response = client.post(
        f"/api/workflows/{workflow_id}/decision",
        headers={"Authorization": "Bearer local-demo-token"},
        json={"decision": "approve", "reviewer": "Reviewer", "reason": "Too early"},
    )
    assert response.status_code == 409


def test_webhook_hmac_and_event_id_idempotency(client: TestClient, payload: dict):
    body = json.dumps(
        {"event_id": "webhook-event-001", "payload": payload},
        separators=(",", ":"),
    ).encode()
    signature = hmac.new(
        b"local-webhook-secret", body, hashlib.sha256
    ).hexdigest()
    response = client.post(
        "/api/webhooks/inbound",
        content=body,
        headers={"Content-Type": "application/json", "X-GTM-Signature": signature},
    )
    assert response.status_code == 202
    repeated = client.post(
        "/api/webhooks/inbound",
        content=body,
        headers={"Content-Type": "application/json", "X-GTM-Signature": signature},
    )
    assert repeated.status_code == 200
    assert repeated.json()["id"] == response.json()["id"]

    rejected = client.post(
        "/api/webhooks/inbound",
        content=body,
        headers={"Content-Type": "application/json", "X-GTM-Signature": "bad"},
    )
    assert rejected.status_code == 401

