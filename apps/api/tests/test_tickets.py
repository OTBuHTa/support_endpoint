from tests.conftest import register_and_create_workspace


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _setup_workspace_with_client(client):
    tokens = register_and_create_workspace(client, email="owner@example.com", workspace_name="Acme")
    ws_id = client.get("/api/v1/workspaces", headers=auth_header(tokens["access_token"])).json()[0][
        "id"
    ]
    client_id = client.post(
        f"/api/v1/workspaces/{ws_id}/clients",
        json={"full_name": "Jane Doe", "primary_email": "jane@example.com"},
        headers=auth_header(tokens["access_token"]),
    ).json()["id"]
    return tokens, ws_id, client_id


def test_create_ticket_defaults_to_new_status_medium_priority(client):
    tokens, ws_id, client_id = _setup_workspace_with_client(client)

    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets",
        json={"client_id": client_id, "subject": "Cannot log in"},
        headers=auth_header(tokens["access_token"]),
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["status"] == "new"
    assert body["priority"] == "medium"
    assert body["tags"] == []


def test_create_ticket_rejects_client_from_nowhere(client):
    tokens, ws_id, _client_id = _setup_workspace_with_client(client)
    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets",
        json={"client_id": "does-not-exist", "subject": "Ghost client"},
        headers=auth_header(tokens["access_token"]),
    )
    assert resp.status_code == 422


def test_queue_and_category_lookup_and_ticket_linkage(client):
    tokens, ws_id, client_id = _setup_workspace_with_client(client)

    queue_id = client.post(
        f"/api/v1/workspaces/{ws_id}/queues",
        json={"name": "Billing"},
        headers=auth_header(tokens["access_token"]),
    ).json()["id"]
    category_id = client.post(
        f"/api/v1/workspaces/{ws_id}/ticket-categories",
        json={"name": "Refund request"},
        headers=auth_header(tokens["access_token"]),
    ).json()["id"]

    ticket = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets",
        json={
            "client_id": client_id,
            "subject": "Refund please",
            "queue_id": queue_id,
            "category_id": category_id,
            "priority": "high",
        },
        headers=auth_header(tokens["access_token"]),
    )
    assert ticket.status_code == 201
    body = ticket.json()
    assert body["queue_id"] == queue_id
    assert body["category_id"] == category_id
    assert body["priority"] == "high"


def test_valid_status_transition_succeeds(client):
    tokens, ws_id, client_id = _setup_workspace_with_client(client)
    ticket_id = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets",
        json={"client_id": client_id, "subject": "Something broke"},
        headers=auth_header(tokens["access_token"]),
    ).json()["id"]

    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/transition",
        json={"status": "open"},
        headers=auth_header(tokens["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "open"


def test_invalid_status_transition_is_rejected(client):
    tokens, ws_id, client_id = _setup_workspace_with_client(client)
    ticket_id = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets",
        json={"client_id": client_id, "subject": "Something broke"},
        headers=auth_header(tokens["access_token"]),
    ).json()["id"]

    # NEW -> WAITING_CUSTOMER is not an allowed direct transition.
    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/transition",
        json={"status": "waiting_customer"},
        headers=auth_header(tokens["access_token"]),
    )
    assert resp.status_code == 422


def test_assign_ticket_validates_membership_and_records_history(client):
    tokens, ws_id, client_id = _setup_workspace_with_client(client)
    ticket_id = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets",
        json={"client_id": client_id, "subject": "Assign me"},
        headers=auth_header(tokens["access_token"]),
    ).json()["id"]

    owner_user_id = client.get(
        "/api/v1/auth/me", headers=auth_header(tokens["access_token"])
    ).json()["id"]

    # Assign to a random, non-member user id -> rejected.
    bad_assign = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/assign",
        json={"assignee_user_id": "not-a-member"},
        headers=auth_header(tokens["access_token"]),
    )
    assert bad_assign.status_code == 422

    # Assign to the owner (a real member) -> succeeds.
    good_assign = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/assign",
        json={"assignee_user_id": owner_user_id},
        headers=auth_header(tokens["access_token"]),
    )
    assert good_assign.status_code == 200
    assert good_assign.json()["assignee_user_id"] == owner_user_id

    history = client.get(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/assignments",
        headers=auth_header(tokens["access_token"]),
    )
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["assignee_user_id"] == owner_user_id

    # Unassign.
    unassign = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/assign",
        json={"assignee_user_id": None},
        headers=auth_header(tokens["access_token"]),
    )
    assert unassign.status_code == 200
    assert unassign.json()["assignee_user_id"] is None

    history2 = client.get(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/assignments",
        headers=auth_header(tokens["access_token"]),
    ).json()
    assert len(history2) == 2  # assign + unassign, both recorded


def test_ticket_tagging(client):
    tokens, ws_id, client_id = _setup_workspace_with_client(client)
    ticket_id = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets",
        json={"client_id": client_id, "subject": "Tag me"},
        headers=auth_header(tokens["access_token"]),
    ).json()["id"]
    tag_id = client.post(
        f"/api/v1/workspaces/{ws_id}/tags",
        json={"name": "vip", "color": "gold"},
        headers=auth_header(tokens["access_token"]),
    ).json()["id"]

    add_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/tags/{tag_id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert add_resp.status_code == 201
    assert [t["id"] for t in add_resp.json()["tags"]] == [tag_id]

    remove_resp = client.delete(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/tags/{tag_id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert remove_resp.status_code == 200
    assert remove_resp.json()["tags"] == []


def test_ticket_search_and_filters(client):
    tokens, ws_id, client_id = _setup_workspace_with_client(client)
    client.post(
        f"/api/v1/workspaces/{ws_id}/tickets",
        json={"client_id": client_id, "subject": "Password reset needed", "priority": "urgent"},
        headers=auth_header(tokens["access_token"]),
    )
    client.post(
        f"/api/v1/workspaces/{ws_id}/tickets",
        json={"client_id": client_id, "subject": "Feature request", "priority": "low"},
        headers=auth_header(tokens["access_token"]),
    )

    by_q = client.get(
        f"/api/v1/workspaces/{ws_id}/tickets?q=password",
        headers=auth_header(tokens["access_token"]),
    ).json()
    assert by_q["total"] == 1
    assert by_q["items"][0]["subject"] == "Password reset needed"

    by_priority = client.get(
        f"/api/v1/workspaces/{ws_id}/tickets?priority=urgent",
        headers=auth_header(tokens["access_token"]),
    ).json()
    assert by_priority["total"] == 1
