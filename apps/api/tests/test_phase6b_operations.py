from datetime import UTC, datetime, timedelta

from app.models.operations import TicketSLA
from tests.conftest import register_and_create_workspace


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup_ticket(client, *, email: str, workspace_name: str):
    tokens = register_and_create_workspace(client, email=email, workspace_name=workspace_name)
    headers = auth_header(tokens["access_token"])
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    customer_id = client.post(
        f"/api/v1/workspaces/{workspace_id}/clients",
        json={"full_name": "Operations Customer", "primary_email": f"customer+{email}"},
        headers=headers,
    ).json()["id"]
    ticket_id = client.post(
        f"/api/v1/workspaces/{workspace_id}/tickets",
        json={"client_id": customer_id, "subject": "Operations test", "priority": "high"},
        headers=headers,
    ).json()["id"]
    return tokens, headers, workspace_id, ticket_id


def test_task_lifecycle_and_assignment_notification(client):
    tokens, headers, workspace_id, ticket_id = _setup_ticket(
        client, email="ops-task@example.com", workspace_name="Ops Tasks"
    )
    owner_id = client.get("/api/v1/auth/me", headers=headers).json()["id"]

    created = client.post(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/tasks",
        json={
            "title": "Verify customer connectivity",
            "description": "Check the latest diagnostics.",
            "assignee_user_id": owner_id,
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    task_id = created.json()["id"]
    assert created.json()["status"] == "open"

    notification_list = client.get(
        f"/api/v1/workspaces/{workspace_id}/notifications", headers=headers
    )
    assert notification_list.status_code == 200
    assert len(notification_list.json()) == 1
    notification = notification_list.json()[0]
    assert notification["type"] == "task_assigned"

    read = client.post(
        f"/api/v1/workspaces/{workspace_id}/notifications/{notification['id']}/read",
        headers=headers,
    )
    assert read.status_code == 200
    assert read.json()["read_at"] is not None

    done = client.post(
        f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}/status",
        json={"status": "done"},
        headers=headers,
    )
    assert done.status_code == 200
    assert done.json()["status"] == "done"
    assert done.json()["completed_at"] is not None

    repeat = client.post(
        f"/api/v1/workspaces/{workspace_id}/tasks/{task_id}/status",
        json={"status": "cancelled"},
        headers=headers,
    )
    assert repeat.status_code == 422


def test_sla_first_response_and_resolution_are_derived_from_history(client):
    _tokens, headers, workspace_id, ticket_id = _setup_ticket(
        client, email="ops-sla@example.com", workspace_name="Ops SLA"
    )

    initial = client.get(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/sla", headers=headers
    )
    assert initial.status_code == 200, initial.text
    assert initial.json()["first_response_at"] is None
    assert initial.json()["resolved_at"] is None

    conversation_id = client.post(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/conversations",
        json={"channel": "web", "subject": "SLA thread"},
        headers=headers,
    ).json()["id"]
    outbound = client.post(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/conversations/"
        f"{conversation_id}/messages",
        json={"body": "First operator response"},
        headers=headers,
    )
    assert outbound.status_code == 201

    responded = client.get(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/sla", headers=headers
    )
    assert responded.status_code == 200
    assert responded.json()["first_response_at"] is not None

    opened = client.post(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/transition",
        json={"status": "open"},
        headers=headers,
    )
    assert opened.status_code == 200
    resolved = client.post(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/transition",
        json={"status": "resolved"},
        headers=headers,
    )
    assert resolved.status_code == 200

    final_sla = client.get(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/sla", headers=headers
    )
    assert final_sla.status_code == 200
    assert final_sla.json()["resolved_at"] is not None


def test_sla_evaluation_creates_breach_notifications_once(client, db_session_factory):
    _tokens, headers, workspace_id, ticket_id = _setup_ticket(
        client, email="ops-breach@example.com", workspace_name="Ops Breach"
    )
    initial = client.get(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/sla", headers=headers
    )
    assert initial.status_code == 200

    db = db_session_factory()
    try:
        item = db.query(TicketSLA).filter(TicketSLA.ticket_id == ticket_id).one()
        past = datetime.now(UTC) - timedelta(minutes=5)
        item.first_response_due_at = past
        item.resolution_due_at = past
        db.add(item)
        db.commit()
    finally:
        db.close()

    evaluated = client.post(f"/api/v1/workspaces/{workspace_id}/sla/evaluate", headers=headers)
    assert evaluated.status_code == 200, evaluated.text
    assert evaluated.json()["breaches_created"] == 2

    repeated = client.post(f"/api/v1/workspaces/{workspace_id}/sla/evaluate", headers=headers)
    assert repeated.status_code == 200
    assert repeated.json()["breaches_created"] == 0

    notifications = client.get(
        f"/api/v1/workspaces/{workspace_id}/notifications", headers=headers
    )
    assert notifications.status_code == 200
    breach_types = [n["type"] for n in notifications.json()]
    assert breach_types.count("sla_breached") == 2


def test_task_idor_guard_across_workspaces(client):
    _tokens_a, headers_a, workspace_a, ticket_a = _setup_ticket(
        client, email="ops-a@example.com", workspace_name="Ops A"
    )
    task_id = client.post(
        f"/api/v1/workspaces/{workspace_a}/tickets/{ticket_a}/tasks",
        json={"title": "Workspace A task"},
        headers=headers_a,
    ).json()["id"]

    _tokens_b, headers_b, workspace_b, _ticket_b = _setup_ticket(
        client, email="ops-b@example.com", workspace_name="Ops B"
    )
    cross = client.post(
        f"/api/v1/workspaces/{workspace_b}/tasks/{task_id}/status",
        json={"status": "done"},
        headers=headers_b,
    )
    assert cross.status_code == 404
