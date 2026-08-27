from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration. Every value is environment-driven —
    never hardcode secrets, ports, or hosts in application code.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- App identity ---
    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="Customer Service Platform", alias="APP_NAME")

    # --- API ---
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")

    # --- Database ---
    database_url: str = Field(
        default="postgresql+psycopg://csp:csp@postgres:5432/csp",
        alias="DATABASE_URL",
    )

    # --- Redis ---
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")

    # --- Auth / JWT ---
    jwt_secret: str = Field(
        default="replace-with-at-least-32-random-bytes-before-external-access",
        alias="JWT_SECRET",
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_minutes: int = Field(default=15, alias="ACCESS_TOKEN_MINUTES")
    refresh_token_days: int = Field(default=14, alias="REFRESH_TOKEN_DAYS")

    # --- Bootstrap ---
    bootstrap_enabled: bool = Field(default=True, alias="BOOTSTRAP_ENABLED")

    # --- Auth rate limiting (Redis-backed) ---
    auth_rate_limit_enabled: bool = Field(default=False, alias="AUTH_RATE_LIMIT_ENABLED")
    auth_rate_limit_window_seconds: int = Field(default=300, alias="AUTH_RATE_LIMIT_WINDOW_SECONDS")
    auth_rate_limit_ip_attempts: int = Field(default=20, alias="AUTH_RATE_LIMIT_IP_ATTEMPTS")
    auth_rate_limit_account_attempts: int = Field(
        default=10, alias="AUTH_RATE_LIMIT_ACCOUNT_ATTEMPTS"
    )

    # --- Security headers ---
    secure_headers_hsts_enabled: bool = Field(default=False, alias="SECURE_HEADERS_HSTS_ENABLED")

    # --- Reverse proxy trust boundary ---
    forwarded_allow_ips: str = Field(default="127.0.0.1", alias="FORWARDED_ALLOW_IPS")

    # --- CORS ---
    cors_allow_origins: str = Field(default="http://localhost:8180", alias="CORS_ALLOW_ORIGINS")

    # --- Metrics ---
    metrics_bearer_token: str = Field(default="", alias="METRICS_BEARER_TOKEN")

    # --- AI / LLM (wired in Phase 6 — present but inert in Foundation) ---
    llm_enabled: bool = Field(default=False, alias="LLM_ENABLED")
    llm_base_url: str = Field(default="http://host.docker.internal:11434/v1", alias="LLM_BASE_URL")
    llm_model: str = Field(default="qwen2.5:7b", alias="LLM_MODEL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_timeout_seconds: int = Field(default=90, alias="LLM_TIMEOUT_SECONDS")

    # --- Logging ---
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
