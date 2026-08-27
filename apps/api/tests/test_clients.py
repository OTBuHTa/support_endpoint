from tests.conftest import register_and_create_workspace


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _workspace_id(client, token: str) -> str:
    return client.get("/api/v1/workspaces", headers=auth_header(token)).json()[0]["id"]


def test_create_and_get_client(client):
    tokens = register_and_create_workspace(client, email="owner@example.com", workspace_name="Acme")
    ws_id = _workspace_id(client, tokens["access_token"])

    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/clients",
        json={"full_name": "Jane Doe", "primary_email": "jane@example.com"},
        headers=auth_header(tokens["access_token"]),
    )
    assert resp.status_code == 201, resp.text
    client_id = resp.json()["id"]

    get_resp = client.get(
        f"/api/v1/workspaces/{ws_id}/clients/{client_id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["full_name"] == "Jane Doe"


def test_client_requires_valid_organization_in_same_workspace(client):
    tokens = register_and_create_workspace(client, email="owner@example.com", workspace_name="Acme")
    ws_id = _workspace_id(client, tokens["access_token"])

    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/clients",
        json={"full_name": "Jane Doe", "organization_id": "does-not-exist"},
        headers=auth_header(tokens["access_token"]),
    )
    assert resp.status_code == 422


def test_client_organization_linkage(client):
    tokens = register_and_create_workspace(client, email="owner@example.com", workspace_name="Acme")
    ws_id = _workspace_id(client, tokens["access_token"])

    org_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/organizations",
        json={"name": "Widgets Inc", "domain": "widgets.example.com"},
        headers=auth_header(tokens["access_token"]),
    )
    assert org_resp.status_code == 201
    org_id = org_resp.json()["id"]

    client_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/clients",
        json={"full_name": "Jane Doe", "organization_id": org_id},
        headers=auth_header(tokens["access_token"]),
    )
    assert client_resp.status_code == 201
    assert client_resp.json()["organization_id"] == org_id

    filtered = client.get(
        f"/api/v1/workspaces/{ws_id}/clients?organization_id={org_id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert filtered.status_code == 200
    assert filtered.json()["total"] == 1


def test_client_search_is_case_insensitive(client):
    tokens = register_and_create_workspace(client, email="owner@example.com", workspace_name="Acme")
    ws_id = _workspace_id(client, tokens["access_token"])

    client.post(
        f"/api/v1/workspaces/{ws_id}/clients",
        json={"full_name": "Jane Doe", "primary_email": "jane@example.com"},
        headers=auth_header(tokens["access_token"]),
    )
    client.post(
        f"/api/v1/workspaces/{ws_id}/clients",
        json={"full_name": "Bob Smith", "primary_email": "bob@example.com"},
        headers=auth_header(tokens["access_token"]),
    )

    resp = client.get(
        f"/api/v1/workspaces/{ws_id}/clients?q=JANE", headers=auth_header(tokens["access_token"])
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 1
    assert body["items"][0]["full_name"] == "Jane Doe"


def test_client_pagination(client):
    tokens = register_and_create_workspace(client, email="owner@example.com", workspace_name="Acme")
    ws_id = _workspace_id(client, tokens["access_token"])

    for i in range(5):
        client.post(
            f"/api/v1/workspaces/{ws_id}/clients",
            json={"full_name": f"Client {i}"},
            headers=auth_header(tokens["access_token"]),
        )

    page1 = client.get(
        f"/api/v1/workspaces/{ws_id}/clients?limit=2&offset=0",
        headers=auth_header(tokens["access_token"]),
    ).json()
    page2 = client.get(
        f"/api/v1/workspaces/{ws_id}/clients?limit=2&offset=2",
        headers=auth_header(tokens["access_token"]),
    ).json()
    assert page1["total"] == 5
    assert len(page1["items"]) == 2
    assert len(page2["items"]) == 2
    assert page1["items"] != page2["items"]


def test_soft_delete_deactivates_client(client):
    tokens = register_and_create_workspace(client, email="owner@example.com", workspace_name="Acme")
    ws_id = _workspace_id(client, tokens["access_token"])

    create_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/clients",
        json={"full_name": "Jane Doe"},
        headers=auth_header(tokens["access_token"]),
    )
    client_id = create_resp.json()["id"]

    del_resp = client.delete(
        f"/api/v1/workspaces/{ws_id}/clients/{client_id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert del_resp.status_code == 204

    get_resp = client.get(
        f"/api/v1/workspaces/{ws_id}/clients/{client_id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["is_active"] is False


def test_client_contacts_crud(client):
    tokens = register_and_create_workspace(client, email="owner@example.com", workspace_name="Acme")
    ws_id = _workspace_id(client, tokens["access_token"])

    client_id = client.post(
        f"/api/v1/workspaces/{ws_id}/clients",
        json={"full_name": "Jane Doe"},
        headers=auth_header(tokens["access_token"]),
    ).json()["id"]

    add_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/clients/{client_id}/contacts",
        json={"label": "Work mobile", "channel_type": "phone", "value": "+1-555-0100"},
        headers=auth_header(tokens["access_token"]),
    )
    assert add_resp.status_code == 201
    contact_id = add_resp.json()["id"]

    list_resp = client.get(
        f"/api/v1/workspaces/{ws_id}/clients/{client_id}/contacts",
        headers=auth_header(tokens["access_token"]),
    )
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    del_resp = client.delete(
        f"/api/v1/workspaces/{ws_id}/clients/{client_id}/contacts/{contact_id}",
        headers=auth_header(tokens["access_token"]),
    )
    assert del_resp.status_code == 204

    list_resp2 = client.get(
        f"/api/v1/workspaces/{ws_id}/clients/{client_id}/contacts",
        headers=auth_header(tokens["access_token"]),
    )
    assert list_resp2.json() == []
