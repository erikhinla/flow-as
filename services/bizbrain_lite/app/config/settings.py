from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bizbrain_env: str = "dev"
    bizbrain_api_token: str = "change-me"
    bizbrain_redis_url: str = "redis://localhost:6379/0"

    notion_api_key: str = ""
    notion_tasks_db_id: str = ""
    notion_artifacts_db_id: str = ""
    notion_handoffs_db_id: str = ""
    notion_agent_status_db_id: str = ""
    notion_memory_db_id: str = ""

    social_hub_api_origin: str = "http://localhost:8000"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

