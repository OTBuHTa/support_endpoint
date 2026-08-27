from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_JWT_SECRET = "replace-with-at-least-32-random-bytes-before-external-access"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="Customer Service Platform", alias="APP_NAME")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    database_url: str = Field(
        default="postgresql+psycopg://csp:csp@postgres:5432/csp",
        alias="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", alias="REDIS_URL")
    jwt_secret: str = Field(default=DEFAULT_JWT_SECRET, alias="JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    access_token_minutes: int = Field(default=15, alias="ACCESS_TOKEN_MINUTES")
    refresh_token_days: int = Field(default=14, alias="REFRESH_TOKEN_DAYS")
    bootstrap_enabled: bool = Field(default=True, alias="BOOTSTRAP_ENABLED")
    auth_rate_limit_enabled: bool = Field(default=False, alias="AUTH_RATE_LIMIT_ENABLED")
    auth_rate_limit_window_seconds: int = Field(default=300, alias="AUTH_RATE_LIMIT_WINDOW_SECONDS")
    auth_rate_limit_ip_attempts: int = Field(default=20, alias="AUTH_RATE_LIMIT_IP_ATTEMPTS")
    auth_rate_limit_account_attempts: int = Field(
        default=10, alias="AUTH_RATE_LIMIT_ACCOUNT_ATTEMPTS"
    )
    secure_headers_hsts_enabled: bool = Field(default=False, alias="SECURE_HEADERS_HSTS_ENABLED")
    forwarded_allow_ips: str = Field(default="127.0.0.1", alias="FORWARDED_ALLOW_IPS")
    cors_allow_origins: str = Field(default="http://localhost:8180", alias="CORS_ALLOW_ORIGINS")
    metrics_bearer_token: str = Field(default="", alias="METRICS_BEARER_TOKEN")
    sla_scheduler_interval_seconds: int = Field(default=60, alias="SLA_SCHEDULER_INTERVAL_SECONDS")
    attachment_max_bytes: int = Field(default=5 * 1024 * 1024, alias="ATTACHMENT_MAX_BYTES")
    attachment_workspace_quota_bytes: int = Field(
        default=512 * 1024 * 1024,
        alias="ATTACHMENT_WORKSPACE_QUOTA_BYTES",
    )

    llm_enabled: bool = Field(default=False, alias="LLM_ENABLED")
    llm_base_url: str = Field(default="http://host.docker.internal:11434/v1", alias="LLM_BASE_URL")
    llm_model: str = Field(default="qwen2.5:7b", alias="LLM_MODEL")
    llm_api_key: str = Field(default="", alias="LLM_API_KEY")
    llm_timeout_seconds: int = Field(default=90, alias="LLM_TIMEOUT_SECONDS")
    llm_workspace_requests_per_minute: int = Field(
        default=12, alias="LLM_WORKSPACE_REQUESTS_PER_MINUTE"
    )
    llm_circuit_failure_threshold: int = Field(default=3, alias="LLM_CIRCUIT_FAILURE_THRESHOLD")
    llm_circuit_cooldown_seconds: int = Field(default=30, alias="LLM_CIRCUIT_COOLDOWN_SECONDS")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if not self.is_production:
            return self
        errors: list[str] = []
        if self.jwt_secret == DEFAULT_JWT_SECRET or len(self.jwt_secret) < 32:
            errors.append("JWT_SECRET must be replaced with at least 32 characters")
        if self.bootstrap_enabled:
            errors.append("BOOTSTRAP_ENABLED must be false")
        if not self.auth_rate_limit_enabled:
            errors.append("AUTH_RATE_LIMIT_ENABLED must be true")
        if not self.secure_headers_hsts_enabled:
            errors.append("SECURE_HEADERS_HSTS_ENABLED must be true")
        if not self.cors_origins_list:
            errors.append("CORS_ALLOW_ORIGINS must not be empty")
        if len(self.metrics_bearer_token) < 32:
            errors.append("METRICS_BEARER_TOKEN must contain at least 32 characters")
        if self.sla_scheduler_interval_seconds < 10:
            errors.append("SLA_SCHEDULER_INTERVAL_SECONDS must be at least 10")
        if self.attachment_max_bytes <= 0:
            errors.append("ATTACHMENT_MAX_BYTES must be greater than zero")
        if self.attachment_workspace_quota_bytes < self.attachment_max_bytes:
            errors.append("ATTACHMENT_WORKSPACE_QUOTA_BYTES must be >= ATTACHMENT_MAX_BYTES")
        if errors:
            raise ValueError("Unsafe production configuration: " + "; ".join(errors))
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
