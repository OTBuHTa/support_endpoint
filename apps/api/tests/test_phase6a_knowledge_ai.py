import pytest

from app.ai.gateway import GatewayResult, LLMGateway, redact_sensitive
from app.core.config import Settings
from app.models.ticket_enums import TicketStatus
from tests.conftest import register_and_create_workspace


def auth_header(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _setup_ticket(client, *, email: str, workspace_name: str):
    tokens = register_and_create_workspace(client, email=email, workspace_name=workspace_name)
    headers = auth_header(tokens["access_token"])
    workspace_id = client.get("/api/v1/workspaces", headers=headers).json()[0]["id"]
    customer_id = client.post(
        f"/api/v1/workspaces/{workspace_id}/clients",
        json={
            "full_name": "Example Customer",
            "primary_email": "customer@example.com",
            "primary_phone": "+420 777 123 456",
        },
        headers=headers,
    ).json()["id"]
    ticket_id = client.post(
        f"/api/v1/workspaces/{workspace_id}/tickets",
        json={
            "client_id": customer_id,
            "subject": "VPN cannot connect",
            "description": "Contact customer@example.com or +420 777 123 456",
        },
        headers=headers,
    ).json()["id"]
    return tokens, workspace_id, ticket_id


def test_redaction_removes_email_and_phone_before_llm():
    value = redact_sensitive("Mail jane@example.com or call +420 777 123 456 today")
    assert "jane@example.com" not in value
    assert "+420 777 123 456" not in value
    assert "[REDACTED_EMAIL]" in value
    assert "[REDACTED_PHONE]" in value


def test_gateway_transmits_redacted_prompt(monkeypatch):
    captured: dict = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "safe proposal"}}]}

    class RecordingClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, url, *, headers, json):
            captured["url"] = url
            captured["json"] = json
            return FakeResponse()

    LLMGateway.reset_circuit()
    monkeypatch.setattr("app.ai.gateway.httpx.Client", RecordingClient)
    gateway = LLMGateway(Settings(LLM_ENABLED=True))
    result = gateway.suggest(
        system_prompt="advisory only",
        user_prompt="Contact jane@example.com at +420 777 123 456",
    )
    sent = captured["json"]["messages"][1]["content"]
    assert "jane@example.com" not in sent
    assert "+420 777 123 456" not in sent
    assert "[REDACTED_EMAIL]" in sent
    assert "[REDACTED_PHONE]" in sent
    assert result.text == "safe proposal"


def test_circuit_breaker_is_shared_across_gateway_instances(monkeypatch):
    class BrokenClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def post(self, *args, **kwargs):
            raise RuntimeError("model endpoint down")

    settings = Settings(
        LLM_ENABLED=True,
        LLM_CIRCUIT_FAILURE_THRESHOLD=2,
        LLM_CIRCUIT_COOLDOWN_SECONDS=30,
    )
    LLMGateway.reset_circuit()
    monkeypatch.setattr("app.ai.gateway.httpx.Client", BrokenClient)
    first = LLMGateway(settings)
    second = LLMGateway(settings)

    with pytest.raises(RuntimeError, match="model endpoint down"):
        first.suggest(system_prompt="x", user_prompt="one")
    with pytest.raises(RuntimeError, match="model endpoint down"):
        first.suggest(system_prompt="x", user_prompt="two")
    with pytest.raises(RuntimeError, match="circuit breaker is open"):
        second.suggest(system_prompt="x", user_prompt="three")
    LLMGateway.reset_circuit()


def test_knowledge_article_crud_and_workspace_idor(client):
    tokens_a = register_and_create_workspace(
        client, email="kb-a@example.com", workspace_name="Knowledge A"
    )
    headers_a = auth_header(tokens_a["access_token"])
    workspace_a = client.get("/api/v1/workspaces", headers=headers_a).json()[0]["id"]

    created = client.post(
        f"/api/v1/workspaces/{workspace_a}/knowledge",
        json={"title": "Reset VPN", "body": "Restart the tunnel client.", "status": "published"},
        headers=headers_a,
    )
    assert created.status_code == 201, created.text
    article_id = created.json()["id"]

    listing = client.get(f"/api/v1/workspaces/{workspace_a}/knowledge", headers=headers_a)
    assert listing.status_code == 200
    assert [item["id"] for item in listing.json()] == [article_id]

    tokens_b = register_and_create_workspace(
        client, email="kb-b@example.com", workspace_name="Knowledge B"
    )
    headers_b = auth_header(tokens_b["access_token"])
    workspace_b = client.get("/api/v1/workspaces", headers=headers_b).json()[0]["id"]
    cross = client.get(
        f"/api/v1/workspaces/{workspace_b}/knowledge/{article_id}", headers=headers_b
    )
    assert cross.status_code == 404


def test_ai_suggestion_is_advisory_and_does_not_mutate_ticket(client, monkeypatch):
    tokens, workspace_id, ticket_id = _setup_ticket(
        client, email="ai-owner@example.com", workspace_name="AI Assist"
    )
    headers = auth_header(tokens["access_token"])

    published = client.post(
        f"/api/v1/workspaces/{workspace_id}/knowledge",
        json={
            "title": "VPN reset",
            "body": "Ask the customer to restart the VPN client.",
            "status": "published",
        },
        headers=headers,
    )
    assert published.status_code == 201

    def fake_suggest(self, *, system_prompt: str, user_prompt: str):
        assert "customer@example.com" in user_prompt
        redacted = redact_sensitive(user_prompt)
        assert "customer@example.com" not in redacted
        assert "+420 777 123 456" not in redacted
        assert "modified infrastructure" in system_prompt
        return GatewayResult(
            text="Proposed reply: please restart the VPN client and retry.",
            redacted_prompt=redacted,
        )

    monkeypatch.setattr("app.ai.gateway.LLMGateway.suggest", fake_suggest)
    monkeypatch.setattr("app.services.knowledge_service.LLMGateway.suggest", fake_suggest)

    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/ai/suggestions",
        json={"kind": "reply"},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    assert response.json()["kind"] == "reply"
    assert response.json()["response_text"].startswith("Proposed reply")

    ticket = client.get(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}", headers=headers
    )
    assert ticket.status_code == 200
    assert ticket.json()["status"] == TicketStatus.NEW.value


def test_ai_assist_disabled_is_fail_closed_without_network(client):
    tokens, workspace_id, ticket_id = _setup_ticket(
        client, email="ai-disabled@example.com", workspace_name="AI Disabled"
    )
    headers = auth_header(tokens["access_token"])
    response = client.post(
        f"/api/v1/workspaces/{workspace_id}/tickets/{ticket_id}/ai/suggestions",
        json={"kind": "summary"},
        headers=headers,
    )
    assert response.status_code == 422
