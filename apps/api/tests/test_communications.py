from tests.conftest import register_and_create_workspace


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup_ticket(client, *, email: str, workspace_name: str):
    tokens = register_and_create_workspace(client, email=email, workspace_name=workspace_name)
    headers = auth_header(tokens["access_token"])
    ws_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    client_id = client.post(
        f"/api/v1/workspaces/{ws_id}/clients",
        json={"full_name": "Customer", "primary_email": f"customer+{email}"},
        headers=headers,
    ).json()["id"]
    ticket_id = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets",
        json={"client_id": client_id, "subject": "Need help"},
        headers=headers,
    ).json()["id"]
    return tokens, ws_id, ticket_id


def test_conversation_messages_and_internal_notes_are_separate(client):
    tokens, ws_id, ticket_id = _setup_ticket(
        client, email="phase5-owner@example.com", workspace_name="Phase5"
    )
    headers = auth_header(tokens["access_token"])

    conversation = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/conversations",
        json={"channel": "email", "subject": "Email thread", "external_thread_ref": "t-1"},
        headers=headers,
    )
    assert conversation.status_code == 201, conversation.text
    conversation_id = conversation.json()["id"]

    outbound = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/conversations/"
        f"{conversation_id}/messages",
        json={"body": "We are looking into this."},
        headers=headers,
    )
    assert outbound.status_code == 201, outbound.text
    assert outbound.json()["direction"] == "outbound"

    inbound = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/conversations/"
        f"{conversation_id}/messages/inbound",
        json={"body": "Thank you", "external_message_ref": "m-42"},
        headers=headers,
    )
    assert inbound.status_code == 201, inbound.text
    assert inbound.json()["direction"] == "inbound"
    assert inbound.json()["author_user_id"] is None

    note = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/internal-notes",
        json={"body": "Operator-only context"},
        headers=headers,
    )
    assert note.status_code == 201, note.text

    messages = client.get(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/conversations/"
        f"{conversation_id}/messages",
        headers=headers,
    )
    assert messages.status_code == 200
    assert [m["body"] for m in messages.json()] == ["We are looking into this.", "Thank you"]
    assert all(m["body"] != "Operator-only context" for m in messages.json())

    notes = client.get(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/internal-notes", headers=headers
    )
    assert notes.status_code == 200
    assert [n["body"] for n in notes.json()] == ["Operator-only context"]


def test_message_attachment_round_trip_and_hash(client):
    tokens, ws_id, ticket_id = _setup_ticket(
        client, email="attachment-owner@example.com", workspace_name="Attachments"
    )
    headers = auth_header(tokens["access_token"])
    conversation_id = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/conversations",
        json={"channel": "web"},
        headers=headers,
    ).json()["id"]
    message_id = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/conversations/"
        f"{conversation_id}/messages",
        json={"body": "See attached"},
        headers=headers,
    ).json()["id"]

    upload = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/conversations/"
        f"{conversation_id}/messages/{message_id}/attachments",
        files={"file": ("hello.txt", b"hello phase 5", "text/plain")},
        headers=headers,
    )
    assert upload.status_code == 201, upload.text
    body = upload.json()
    assert body["filename"] == "hello.txt"
    assert body["size_bytes"] == len(b"hello phase 5")
    assert len(body["sha256"]) == 64

    download = client.get(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/attachments/{body['id']}",
        headers=headers,
    )
    assert download.status_code == 200
    assert download.content == b"hello phase 5"
    assert download.headers["content-type"].startswith("text/plain")


def test_attachment_size_limit_is_enforced(client):
    tokens, ws_id, ticket_id = _setup_ticket(
        client, email="large-owner@example.com", workspace_name="LargeAttachments"
    )
    headers = auth_header(tokens["access_token"])
    conversation_id = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/conversations",
        json={"channel": "web"},
        headers=headers,
    ).json()["id"]
    message_id = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/conversations/"
        f"{conversation_id}/messages",
        json={"body": "oversize test"},
        headers=headers,
    ).json()["id"]

    response = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/conversations/"
        f"{conversation_id}/messages/{message_id}/attachments",
        files={"file": ("large.bin", b"x" * (5 * 1024 * 1024 + 1), "application/octet-stream")},
        headers=headers,
    )
    assert response.status_code == 422


def test_conversation_idor_guard_across_workspaces(client):
    tokens_a, ws_a, ticket_a = _setup_ticket(
        client, email="a-phase5@example.com", workspace_name="Workspace A"
    )
    headers_a = auth_header(tokens_a["access_token"])
    conversation_id = client.post(
        f"/api/v1/workspaces/{ws_a}/tickets/{ticket_a}/conversations",
        json={"channel": "chat"},
        headers=headers_a,
    ).json()["id"]

    tokens_b, ws_b, ticket_b = _setup_ticket(
        client, email="b-phase5@example.com", workspace_name="Workspace B"
    )
    headers_b = auth_header(tokens_b["access_token"])

    response = client.get(
        f"/api/v1/workspaces/{ws_b}/tickets/{ticket_b}/conversations/"
        f"{conversation_id}/messages",
        headers=headers_b,
    )
    assert response.status_code == 404
