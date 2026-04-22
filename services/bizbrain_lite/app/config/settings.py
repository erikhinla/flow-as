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

    # JWT / Auth settings
    jwt_secret_key: str = "change-me-to-a-long-random-secret"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60 * 24  # 24 hours
    magic_link_expire_minutes: int = 15


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

