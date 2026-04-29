from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    bizbrain_env: str = "dev"
    bizbrain_api_token: str = "change-me"
    bizbrain_redis_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("BIZBRAIN_REDIS_URL", "REDIS_URL"),
    )

    social_hub_api_origin: str = "http://localhost:8000"
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"
    discord_webhook_url: str = ""
    output_dir: str = "/app/runtime/reviews"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

