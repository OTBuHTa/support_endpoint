from tests.conftest import bootstrap_and_login, register_and_create_workspace


def auth_header(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def test_workspace_a_cannot_access_workspace_b(client):
    """Mandatory regression: a member of workspace A must not be able
    to read workspace B by guessing/knowing its id.
    """
    tokens_a = register_and_create_workspace(
        client, email="owner-a@example.com", workspace_name="Acme A"
    )
    tokens_b = register_and_create_workspace(
        client, email="owner-b@example.com", workspace_name="Acme B"
    )

    my_workspaces_b = client.get(
        "/api/v1/workspaces", headers=auth_header(tokens_b["access_token"])
    ).json()
    workspace_b_id = my_workspaces_b[0]["id"]

    # Owner of workspace A tries to read workspace B directly by id.
    resp = client.get(
        f"/api/v1/workspaces/{workspace_b_id}", headers=auth_header(tokens_a["access_token"])
    )
    assert resp.status_code == 404

    # Same for the permission-introspection endpoint.
    resp2 = client.get(
        f"/api/v1/workspaces/{workspace_b_id}/my-permissions",
        headers=auth_header(tokens_a["access_token"]),
    )
    assert resp2.status_code == 404


def test_unauthorized_user_cannot_access_workspace_without_membership(client):
    tokens_owner = register_and_create_workspace(
        client, email="owner@example.com", workspace_name="Acme"
    )
    workspaces = client.get(
        "/api/v1/workspaces", headers=auth_header(tokens_owner["access_token"])
    ).json()
    workspace_id = workspaces[0]["id"]

    # A second, genuinely separate account with no membership anywhere
    # relevant, attempts to read the first user's workspace by id.
    tokens_outsider = register_and_create_workspace(
        client, email="outsider@example.com", workspace_name="Someone Else Co"
    )
    resp = client.get(
        f"/api/v1/workspaces/{workspace_id}",
        headers=auth_header(tokens_outsider["access_token"]),
    )
    assert resp.status_code == 404


def test_administrator_can_call_admin_only_endpoint(client):
    tokens = register_and_create_workspace(client, email="admin@example.com", workspace_name="Acme")
    workspace_id = client.get(
        "/api/v1/workspaces", headers=auth_header(tokens["access_token"])
    ).json()[0]["id"]

    resp = client.get(
        f"/api/v1/workspaces/{workspace_id}/admin-only-ping",
        headers=auth_header(tokens["access_token"]),
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_operator_cannot_acquire_admin_permissions(client):
    """Mandatory regression: a member with the Operator role must be
    denied on an endpoint that requires an Administrator-only
    permission (users.manage), even though they are a legitimate
    member of the workspace.
    """
    owner_tokens = register_and_create_workspace(
        client, email="owner@example.com", workspace_name="Acme"
    )
    workspace_id = client.get(
        "/api/v1/workspaces", headers=auth_header(owner_tokens["access_token"])
    ).json()[0]["id"]

    # Create a second user and attach them to the same workspace with
    # the Operator role directly at the DB layer (there is no
    # user-invitation endpoint yet in Foundation — that is Phase 3+).
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
            email="operator@example.com",
            password_hash=hash_password("correct-horse-battery-staple"),
            full_name="Operator",
        )
        db.add(operator_user)
        db.flush()
        db.add(
            WorkspaceMembership(
                id=new_uuid(),
                workspace_id=workspace_id,
                user_id=operator_user.id,
                role_id=operator_role.id,
            )
        )
        db.commit()
    finally:
        db.close()

    operator_login = client.post(
        "/api/v1/auth/login",
        json={"email": "operator@example.com", "password": "correct-horse-battery-staple"},
    )
    assert operator_login.status_code == 200
    operator_token = operator_login.json()["access_token"]

    # Operator has tickets/clients permissions but NOT users.manage.
    resp = client.get(
        f"/api/v1/workspaces/{workspace_id}/admin-only-ping",
        headers=auth_header(operator_token),
    )
    assert resp.status_code == 404  # deny-by-default: not found, not just forbidden

    # Sanity: the operator IS a real member and can read their own permissions.
    perms_resp = client.get(
        f"/api/v1/workspaces/{workspace_id}/my-permissions",
        headers=auth_header(operator_token),
    )
    assert perms_resp.status_code == 200
    assert "users.manage" not in perms_resp.json()["permissions"]
    assert "tickets.read" in perms_resp.json()["permissions"]


def test_bootstrap_owner_is_administrator_of_bootstrap_workspace(client):
    """Sanity check that bootstrap (the one-time flow) still produces
    a working Administrator membership, exercised via a real endpoint
    rather than only inspecting the database.
    """
    tokens = bootstrap_and_login(client, email="first-owner@example.com", workspace_name="First Co")
    workspace_id = client.get(
        "/api/v1/workspaces", headers=auth_header(tokens["access_token"])
    ).json()[0]["id"]
    resp = client.get(
        f"/api/v1/workspaces/{workspace_id}/admin-only-ping",
        headers=auth_header(tokens["access_token"]),
    )
    assert resp.status_code == 200
