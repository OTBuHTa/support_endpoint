from tests.conftest import register_and_create_workspace


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_user(client, email: str) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Str0ng-passphrase!", "full_name": "Portal User"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_portal_link_and_ticket_ownership(client):
    operator = register_and_create_workspace(
        client, email="portal-owner@example.com", workspace_name="Portal Workspace"
    )
    operator_headers = auth_header(operator["access_token"])
    workspace_id = client.get("/api/v1/workspaces", headers=operator_headers).json()[0]["id"]
    client_id = client.post(
        f"/api/v1/workspaces/{workspace_id}/clients",
        json={"full_name": "Portal Customer", "primary_email": "customer@example.com"},
        headers=operator_headers,
    ).json()["id"]

    portal_tokens = register_user(client, "customer-login@example.com")
    portal_headers = auth_header(portal_tokens["access_token"])
    linked = client.post(
        f"/api/v1/workspaces/{workspace_id}/clients/{client_id}/portal-link",
        json={"user_email": "customer-login@example.com"},
        headers=operator_headers,
    )
    assert linked.status_code == 201, linked.text
    link_id = linked.json()["id"]

    accounts = client.get("/api/v1/portal/accounts", headers=portal_headers)
    assert accounts.status_code == 200
    assert accounts.json()[0]["link_id"] == link_id

    created = client.post(
        f"/api/v1/portal/accounts/{link_id}/tickets",
        json={"subject": "Need help", "description": "Portal-created ticket", "priority": "high"},
        headers=portal_headers,
    )
    assert created.status_code == 201, created.text
    assert created.json()["client_id"] == client_id
    ticket_id = created.json()["id"]

    reply = client.post(
        f"/api/v1/portal/accounts/{link_id}/tickets/{ticket_id}/messages",
        json={"body": "Customer follow-up"},
        headers=portal_headers,
    )
    assert reply.status_code == 201, reply.text
    assert reply.json()["direction"] == "inbound"

    messages = client.get(
        f"/api/v1/portal/accounts/{link_id}/tickets/{ticket_id}/messages",
        headers=portal_headers,
    )
    assert messages.status_code == 200
    assert [item["body"] for item in messages.json()] == ["Customer follow-up"]


def test_portal_link_idor_is_normalized_to_404(client):
    operator = register_and_create_workspace(
        client, email="portal-owner-idor@example.com", workspace_name="Portal IDOR"
    )
    operator_headers = auth_header(operator["access_token"])
    workspace_id = client.get("/api/v1/workspaces", headers=operator_headers).json()[0]["id"]
    client_id = client.post(
        f"/api/v1/workspaces/{workspace_id}/clients",
        json={"full_name": "Portal Customer", "primary_email": "idor@example.com"},
        headers=operator_headers,
    ).json()["id"]
    owner_tokens = register_user(client, "portal-a@example.com")
    attacker_tokens = register_user(client, "portal-b@example.com")
    linked = client.post(
        f"/api/v1/workspaces/{workspace_id}/clients/{client_id}/portal-link",
        json={"user_email": "portal-a@example.com"},
        headers=operator_headers,
    ).json()

    cross = client.get(
        f"/api/v1/portal/accounts/{linked['id']}/tickets",
        headers=auth_header(attacker_tokens["access_token"]),
    )
    assert cross.status_code == 404

    owner_accounts = client.get(
        "/api/v1/portal/accounts", headers=auth_header(owner_tokens["access_token"])
    )
    assert owner_accounts.status_code == 200
    assert len(owner_accounts.json()) == 1
