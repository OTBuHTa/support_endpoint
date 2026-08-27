from app.api.v1 import metrics as metrics_module
from app.core.config import Settings


def test_metrics_hidden_without_configuration(client, monkeypatch):
    monkeypatch.setattr(metrics_module, "get_settings", lambda: Settings(_env_file=None))
    response = client.get("/api/v1/metrics")
    assert response.status_code == 404


def test_metrics_requires_bearer_token(client, monkeypatch):
    settings = Settings(_env_file=None, METRICS_BEARER_TOKEN="test-metrics-token")
    monkeypatch.setattr(metrics_module, "get_settings", lambda: settings)

    unauthorized = client.get("/api/v1/metrics")
    assert unauthorized.status_code == 401

    response = client.get(
        "/api/v1/metrics",
        headers={"Authorization": "Bearer test-metrics-token"},
    )
    assert response.status_code == 200
    assert "csp_http_requests_total" in response.text
    assert "csp_http_requests_in_flight" in response.text
    assert "csp_http_request_duration_seconds_sum" in response.text
