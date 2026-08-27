from app.version import API_VERSION, BUILD_REVISION


def test_health_ok(client):
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["version"] == API_VERSION
    assert resp.json()["build_revision"] == BUILD_REVISION


def test_ready_ok(client):
    resp = client.get("/api/v1/ready")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
    assert resp.json()["checks"]["database"] == "ok"
    assert resp.json()["checks"]["redis"] == "ok"
    assert resp.json()["version"] == API_VERSION
    assert resp.json()["build_revision"] == BUILD_REVISION
