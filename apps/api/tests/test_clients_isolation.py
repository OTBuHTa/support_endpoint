from tests.conftest import register_and_create_workspace


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _workspace_id(client, token: str) -> str:
    return client.get("/api/v1/workspaces", headers=auth_header(token)).json()[0]["id"]


def test_workspace_a_cannot_read_or_list_workspace_b_clients(client):
    tokens_a = register_and_create_workspace(client, email="a@example.com", workspace_name="A Co")
    tokens_b = register_and_create_workspace(client, email="b@example.com", workspace_name="B Co")
    ws_b = _workspace_id(client, tokens_b["access_token"])

    created = client.post(
        f"/api/v1/workspaces/{ws_b}/clients",
        json={"full_name": "B's Customer"},
        headers=auth_header(tokens_b["access_token"]),
    )
    assert created.status_code == 201
    client_id_in_b = created.json()["id"]

    # A tries to list B's workspace clients directly (blocked at the
    # membership layer — A has no membership in ws_b at all).
    list_resp = client.get(
        f"/api/v1/workspaces/{ws_b}/clients", headers=auth_header(tokens_a["access_token"])
    )
    assert list_resp.status_code == 404

    # A tries to read the specific client record by id via B's workspace path.
    get_resp = client.get(
        f"/api/v1/workspaces/{ws_b}/clients/{client_id_in_b}",
        headers=auth_header(tokens_a["access_token"]),
    )
    assert get_resp.status_code == 404


def test_client_id_from_one_workspace_not_resolvable_via_another_workspace_path(client):
    """Object-level IDOR guard: even if an attacker is a legitimate
    member of workspace A and somehow learns a valid client_id that
    actually belongs to workspace B, requesting it through workspace
    A's path must 404 — the repository filters by workspace_id AND id.
    """
    tokens_a = register_and_create_workspace(client, email="a2@example.com", workspace_name="A2 Co")
    tokens_b = register_and_create_workspace(client, email="b2@example.com", workspace_name="B2 Co")
    ws_a = _workspace_id(client, tokens_a["access_token"])
    ws_b = _workspace_id(client, tokens_b["access_token"])

    client_id_in_b = client.post(
        f"/api/v1/workspaces/{ws_b}/clients",
        json={"full_name": "B2's Customer"},
        headers=auth_header(tokens_b["access_token"]),
    ).json()["id"]

    # A is a legitimate Administrator of ws_a (passes the membership
    # check) but the client_id belongs to ws_b — must still 404.
    resp = client.get(
        f"/api/v1/workspaces/{ws_a}/clients/{client_id_in_b}",
        headers=auth_header(tokens_a["access_token"]),
    )
    assert resp.status_code == 404


def test_operator_can_read_but_not_write_clients(client):
    owner_tokens = register_and_create_workspace(
        client, email="owner3@example.com", workspace_name="Acme3"
    )
    ws_id = _workspace_id(client, owner_tokens["access_token"])

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
        operator_user = User(
            id=new_uuid(),
            email="operator3@example.com",
            password_hash=hash_password("correct-horse-battery-staple"),
            full_name="Operator",
        )
        db.add(operator_user)
        db.flush()
        db.add(
            WorkspaceMembership(
                id=new_uuid(),
                workspace_id=ws_id,
                user_id=operator_user.id,
                role_id=operator_role.id,
            )
        )
        db.commit()
    finally:
        db.close()

    operator_token = client.post(
        "/api/v1/auth/login",
        json={"email": "operator3@example.com", "password": "correct-horse-battery-staple"},
    ).json()["access_token"]

    # Operator role has clients.read but not clients.write.
    list_resp = client.get(
        f"/api/v1/workspaces/{ws_id}/clients", headers=auth_header(operator_token)
    )
    assert list_resp.status_code == 200

    create_resp = client.post(
        f"/api/v1/workspaces/{ws_id}/clients",
        json={"full_name": "Should Be Denied"},
        headers=auth_header(operator_token),
    )
    assert create_resp.status_code == 404  # deny-by-default, not 403 (see ADR-003)


def test_client_role_has_no_internal_crm_access(client):
    """The system 'client' role intentionally carries zero internal
    permissions (see app/authz/permissions.py) — a client-portal user
    (Phase 7) must never reach internal CRM endpoints even if somehow
    given a membership row.
    """
    owner_tokens = register_and_create_workspace(
        client, email="owner4@example.com", workspace_name="Acme4"
    )
    ws_id = _workspace_id(client, owner_tokens["access_token"])

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
            email="portaluser@example.com",
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
        json={"email": "portaluser@example.com", "password": "correct-horse-battery-staple"},
    ).json()["access_token"]

    resp = client.get(f"/api/v1/workspaces/{ws_id}/clients", headers=auth_header(portal_token))
    assert resp.status_code == 404
