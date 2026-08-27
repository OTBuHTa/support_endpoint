import pytest
from pydantic import ValidationError

from app.core.config import DEFAULT_JWT_SECRET, Settings
import app.main as main_module


def production_settings(**overrides) -> Settings:
    values = {
        "APP_ENV": "production",
        "JWT_SECRET": "production-secret-at-least-32-characters-long",
        "BOOTSTRAP_ENABLED": False,
        "AUTH_RATE_LIMIT_ENABLED": True,
        "SECURE_HEADERS_HSTS_ENABLED": True,
        "CORS_ALLOW_ORIGINS": "https://support.example.com",
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"JWT_SECRET": DEFAULT_JWT_SECRET}, "JWT_SECRET"),
        ({"BOOTSTRAP_ENABLED": True}, "BOOTSTRAP_ENABLED"),
        ({"AUTH_RATE_LIMIT_ENABLED": False}, "AUTH_RATE_LIMIT_ENABLED"),
        ({"SECURE_HEADERS_HSTS_ENABLED": False}, "SECURE_HEADERS_HSTS_ENABLED"),
        ({"CORS_ALLOW_ORIGINS": ""}, "CORS_ALLOW_ORIGINS"),
    ],
)
def test_production_settings_fail_closed(override, message):
    with pytest.raises(ValidationError, match=message):
        production_settings(**override)


def test_production_app_disables_api_docs(monkeypatch):
    monkeypatch.setattr(main_module, "settings", production_settings())
    app = main_module.create_app()
    assert app.docs_url is None
    assert app.openapi_url is None
    assert app.redoc_url is None


def test_development_app_keeps_api_docs(monkeypatch):
    monkeypatch.setattr(main_module, "settings", Settings(_env_file=None))
    app = main_module.create_app()
    assert app.docs_url == "/docs"
    assert app.openapi_url == "/openapi.json"
