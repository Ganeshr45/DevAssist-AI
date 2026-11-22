from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    jwt_secret_key: str
    database_url: str = "postgresql+asyncpg://devassist:devassist@localhost:5432/devassist"
    redis_url: str = "redis://localhost:6379/0"
    frontend_origins: str = "http://localhost:3000"
    access_token_minutes: int = 15
    refresh_token_days: int = 14
    max_upload_mb: int = 20
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    retrieval_top_k: int = 5
    retrieval_min_score: float = 0.20
    chunk_size: int = 1600
    chunk_overlap: int = 200
    rate_limit_per_minute: int = 120
    sentry_dsn: str = ""
    otel_exporter_otlp_endpoint: str = ""
    admin_emails: str = ""
    max_document_chars: int = 2_000_000
    max_pdf_pages: int = 1000
    storage_bucket: str = ""
    storage_region: str = "ap-south-1"
    storage_endpoint_url: str = ""
    max_completion_tokens: int = 2048
    login_attempts_per_window: int = 12
    login_window_seconds: int = 900
    chat_requests_per_minute: int = 20
    uploads_per_hour: int = 10

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret(cls, value: str) -> str:
        if len(value.encode()) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 bytes")
        return value

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.frontend_origins.split(",") if item.strip()]


settings = Settings()
