from tests.conftest import register_and_create_workspace


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _workspace_id(client, token: str) -> str:
    return client.get("/api/v1/workspaces", headers=auth_header(token)).json()[0]["id"]


def _make_ticket(client, token: str, ws_id: str) -> str:
    client_id = client.post(
        f"/api/v1/workspaces/{ws_id}/clients",
        json={"full_name": "Some Customer"},
        headers=auth_header(token),
    ).json()["id"]
    return client.post(
        f"/api/v1/workspaces/{ws_id}/tickets",
        json={"client_id": client_id, "subject": "Test ticket"},
        headers=auth_header(token),
    ).json()["id"]


def test_ticket_id_from_one_workspace_not_resolvable_via_another_workspace_path(client):
    tokens_a = register_and_create_workspace(client, email="ta@example.com", workspace_name="TA Co")
    tokens_b = register_and_create_workspace(client, email="tb@example.com", workspace_name="TB Co")
    ws_a = _workspace_id(client, tokens_a["access_token"])
    ws_b = _workspace_id(client, tokens_b["access_token"])

    ticket_id_in_b = _make_ticket(client, tokens_b["access_token"], ws_b)

    # A is a legitimate member of ws_a, but the ticket belongs to ws_b.
    resp = client.get(
        f"/api/v1/workspaces/{ws_a}/tickets/{ticket_id_in_b}",
        headers=auth_header(tokens_a["access_token"]),
    )
    assert resp.status_code == 404

    # And A cannot list ws_b's tickets at all (no membership there).
    list_resp = client.get(
        f"/api/v1/workspaces/{ws_b}/tickets", headers=auth_header(tokens_a["access_token"])
    )
    assert list_resp.status_code == 404


def _create_operator(client, ws_id: str, email: str) -> str:
    from app.core.security import hash_password
    from app.db.base import new_uuid
    from app.db.session import get_db as real_get_db
    from app.main import app as fastapi_app
    from app.models.user import User
    from app.models.workspace import WorkspaceMembership
    from app.repositories.rbac_repo import RbacRepository

    db_gen = fastapi_app.dependency_overrides[real_get_db]()
    db = next(db_gen)
    try:
        operator_role = RbacRepository(db).get_role_by_name("operator")
        user = User(
            id=new_uuid(),
            email=email,
            password_hash=hash_password("correct-horse-battery-staple"),
            full_name="Operator",
        )
        db.add(user)
        db.flush()
        db.add(
            WorkspaceMembership(
                id=new_uuid(), workspace_id=ws_id, user_id=user.id, role_id=operator_role.id
            )
        )
        db.commit()
    finally:
        db.close()

    return client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correct-horse-battery-staple"},
    ).json()["access_token"]


def test_operator_can_update_but_not_close_ticket(client):
    """Mandatory regression: tickets.close is deliberately withheld
    from Operator (see app/authz/permissions.py) — an Operator can
    move a ticket through most of the lifecycle but cannot close it.
    """
    owner_tokens = register_and_create_workspace(
        client, email="owner5@example.com", workspace_name="Acme5"
    )
    ws_id = _workspace_id(client, owner_tokens["access_token"])
    ticket_id = _make_ticket(client, owner_tokens["access_token"], ws_id)

    operator_token = _create_operator(client, ws_id, "operator5@example.com")

    # Operator can move NEW -> OPEN (tickets.update is sufficient).
    open_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/transition",
        json={"status": "open"},
        headers=auth_header(operator_token),
    )
    assert open_resp.status_code == 200
    assert open_resp.json()["status"] == "open"

    # Operator cannot close it (tickets.close required).
    close_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/transition",
        json={"status": "closed"},
        headers=auth_header(operator_token),
    )
    assert close_resp.status_code == 403

    # The owner (Administrator) CAN close it.
    admin_close = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/transition",
        json={"status": "closed"},
        headers=auth_header(owner_tokens["access_token"]),
    )
    assert admin_close.status_code == 200
    assert admin_close.json()["status"] == "closed"


def test_operator_can_create_and_assign_tickets(client):
    """Phase 4 refinement: Operator gained tickets.assign (typically
    for self-assignment) — verify this actually works end to end.
    """
    owner_tokens = register_and_create_workspace(
        client, email="owner6@example.com", workspace_name="Acme6"
    )
    ws_id = _workspace_id(client, owner_tokens["access_token"])
    operator_token = _create_operator(client, ws_id, "operator6@example.com")
    operator_user_id = client.get("/api/v1/auth/me", headers=auth_header(operator_token)).json()[
        "id"
    ]

    ticket_id = _make_ticket(client, owner_tokens["access_token"], ws_id)

    resp = client.post(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}/assign",
        json={"assignee_user_id": operator_user_id},
        headers=auth_header(operator_token),
    )
    assert resp.status_code == 200
    assert resp.json()["assignee_user_id"] == operator_user_id


def test_client_role_cannot_access_tickets(client):
    owner_tokens = register_and_create_workspace(
        client, email="owner7@example.com", workspace_name="Acme7"
    )
    ws_id = _workspace_id(client, owner_tokens["access_token"])
    ticket_id = _make_ticket(client, owner_tokens["access_token"], ws_id)

    from app.core.security import hash_password
    from app.db.base import new_uuid
    from app.db.session import get_db as real_get_db
    from app.main import app as fastapi_app
    from app.models.user import User
    from app.models.workspace import WorkspaceMembership
    from app.repositories.rbac_repo import RbacRepository

    db_gen = fastapi_app.dependency_overrides[real_get_db]()
    db = next(db_gen)
    try:
        client_role = RbacRepository(db).get_role_by_name("client")
        portal_user = User(
            id=new_uuid(),
            email="portal7@example.com",
            password_hash=hash_password("correct-horse-battery-staple"),
            full_name="Portal User",
        )
        db.add(portal_user)
        db.flush()
        db.add(
            WorkspaceMembership(
                id=new_uuid(), workspace_id=ws_id, user_id=portal_user.id, role_id=client_role.id
            )
        )
        db.commit()
    finally:
        db.close()

    portal_token = client.post(
        "/api/v1/auth/login",
        json={"email": "portal7@example.com", "password": "correct-horse-battery-staple"},
    ).json()["access_token"]

    resp = client.get(
        f"/api/v1/workspaces/{ws_id}/tickets/{ticket_id}", headers=auth_header(portal_token)
    )
    assert resp.status_code == 404
