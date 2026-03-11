from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = Field(default="Agente Vendedor Backend", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    app_debug: bool = Field(default=True, alias="APP_DEBUG")
    app_port: int = Field(default=8000, alias="APP_PORT")

    allowed_origins_raw: str = Field(default="http://localhost:3000", alias="ALLOWED_ORIGINS")

    database_url: str = Field(default="", alias="DATABASE_URL")
    mysql_url: str = Field(default="", alias="MYSQL_URL")
    redis_url: str = Field(default="", alias="REDIS_URL")
    qdrant_url: str = Field(default="", alias="QDRANT_URL")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    openai_timeout_seconds: int = Field(default=30, alias="OPENAI_TIMEOUT_SECONDS")
    chatwoot_base_url: str = Field(default="", alias="CHATWOOT_BASE_URL")
    chatwoot_api_token: str = Field(default="", alias="CHATWOOT_API_TOKEN")
    chatwoot_webhook_secret: str = Field(default="", alias="CHATWOOT_WEBHOOK_SECRET")

    session_secret: str = Field(default="", alias="SESSION_SECRET")
    rate_limit_default_per_min: int = Field(default=100, alias="RATE_LIMIT_DEFAULT_PER_MIN")
    auth_dev_bypass: bool = Field(default=False, alias="AUTH_DEV_BYPASS")
    seed_admin_email: str = Field(default="admin@agentevendedor.example.com", alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str = Field(default="12345678", alias="SEED_ADMIN_PASSWORD")
    seed_tenant_slug: str = Field(default="tenant-lab", alias="SEED_TENANT_SLUG")
    qdrant_collection_name: str = Field(default="knowledge_chunks", alias="QDRANT_COLLECTION_NAME")
    celery_task_always_eager: bool = Field(default=False, alias="CELERY_TASK_ALWAYS_EAGER")

    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
