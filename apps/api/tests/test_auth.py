from tests.conftest import bootstrap_and_login


def test_bootstrap_creates_owner_and_workspace(client):
    tokens = bootstrap_and_login(client, email="owner@example.com", workspace_name="Acme")
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    me = client.get(
        "/api/v1/auth/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert me.status_code == 200
    assert me.json()["email"] == "owner@example.com"


def test_bootstrap_twice_is_rejected(client):
    bootstrap_and_login(client, email="owner@example.com", workspace_name="Acme")
    resp = client.post(
        "/api/v1/auth/bootstrap",
        json={
            "email": "second@example.com",
            "password": "correct-horse-battery-staple",
            "full_name": "Second",
            "workspace_name": "Other",
        },
    )
    assert resp.status_code == 409


def test_login_with_wrong_password_rejected(client):
    bootstrap_and_login(client, email="owner@example.com", workspace_name="Acme")
    resp = client.post(
        "/api/v1/auth/login", json={"email": "owner@example.com", "password": "wrong"}
    )
    assert resp.status_code == 401


def test_refresh_rotates_token_and_invalidates_old_one(client):
    tokens = bootstrap_and_login(client, email="owner@example.com", workspace_name="Acme")

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200
    new_tokens = refreshed.json()
    assert new_tokens["refresh_token"] != tokens["refresh_token"]

    # The old refresh token was single-use and is now revoked.
    reuse_attempt = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse_attempt.status_code == 401


def test_logout_revokes_refresh_token(client):
    tokens = bootstrap_and_login(client, email="owner@example.com", workspace_name="Acme")

    logout_resp = client.post(
        "/api/v1/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_resp.status_code == 204

    reuse_attempt = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse_attempt.status_code == 401


def test_protected_endpoint_rejects_missing_token(client):
    resp = client.get("/api/v1/auth/me")
    assert resp.status_code == 401


def test_protected_endpoint_rejects_garbage_token(client):
    resp = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert resp.status_code == 401
