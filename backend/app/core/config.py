from functools import lru_cache
from pathlib import Path
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
    conversation_context_ttl_seconds: int = Field(default=86400, alias="CONVERSATION_CONTEXT_TTL_SECONDS")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_api_key_file: str = Field(default="", alias="OPENAI_API_KEY_FILE")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(default="text-embedding-3-small", alias="OPENAI_EMBEDDING_MODEL")
    openai_timeout_seconds: int = Field(default=30, alias="OPENAI_TIMEOUT_SECONDS")
    chatwoot_base_url: str = Field(default="", alias="CHATWOOT_BASE_URL")
    chatwoot_api_token: str = Field(default="", alias="CHATWOOT_API_TOKEN")
    chatwoot_webhook_secret: str = Field(default="", alias="CHATWOOT_WEBHOOK_SECRET")
    backend_internal_url: str = Field(default="http://backend:8000", alias="BACKEND_INTERNAL_URL")
    whatsapp_gateway_base_url: str = Field(default="http://whatsapp-gateway:8090", alias="WHATSAPP_GATEWAY_BASE_URL")
    whatsapp_gateway_secret: str = Field(default="", alias="WHATSAPP_GATEWAY_SECRET")

    session_secret: str = Field(default="", alias="SESSION_SECRET")
    rate_limit_default_per_min: int = Field(default=100, alias="RATE_LIMIT_DEFAULT_PER_MIN")
    auth_dev_bypass: bool = Field(default=False, alias="AUTH_DEV_BYPASS")
    seed_admin_email: str = Field(default="admin@agentevendedor.example.com", alias="SEED_ADMIN_EMAIL")
    seed_admin_password: str = Field(default="12345678", alias="SEED_ADMIN_PASSWORD")
    seed_tenant_slug: str = Field(default="tenant-lab", alias="SEED_TENANT_SLUG")
    admin_reset_secret: str = Field(default="", alias="ADMIN_RESET_SECRET")
    qdrant_collection_name: str = Field(default="knowledge_chunks", alias="QDRANT_COLLECTION_NAME")
    celery_task_always_eager: bool = Field(default=False, alias="CELERY_TASK_ALWAYS_EAGER")

    @property
    def allowed_origins(self) -> List[str]:
        return [origin.strip() for origin in self.allowed_origins_raw.split(",") if origin.strip()]

    @property
    def resolved_openai_api_key(self) -> str:
        if self.openai_api_key:
            return self.openai_api_key
        if self.openai_api_key_file:
            try:
                return Path(self.openai_api_key_file).read_text(encoding="utf-8").strip()
            except OSError:
                return ""
        return ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
