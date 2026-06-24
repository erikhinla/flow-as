"""Settings and configuration for BizBrain Lite.

Loads from environment variables with sensible defaults.
Supports both local development and production deployment.
"""

import os
from functools import lru_cache


class Settings:
    """Application settings."""

    # Database
    bizbrain_db_host: str = os.getenv("BIZBRAIN_DB_HOST", "localhost")
    bizbrain_db_port: int = int(os.getenv("BIZBRAIN_DB_PORT", "5432"))
    bizbrain_db_name: str = os.getenv("BIZBRAIN_DB_NAME", "flow_agent_os")
    bizbrain_db_user: str = os.getenv("BIZBRAIN_DB_USER", "flow_user")
    bizbrain_db_password: str = os.getenv("BIZBRAIN_DB_PASSWORD", "flow_password")

    @property
    def database_url(self) -> str:
        """Construct PostgreSQL connection string."""
        return (
            f"postgresql+asyncpg://{self.bizbrain_db_user}:{self.bizbrain_db_password}@"
            f"{self.bizbrain_db_host}:{self.bizbrain_db_port}/{self.bizbrain_db_name}"
        )

    # Redis
    bizbrain_redis_url: str = os.getenv("BIZBRAIN_REDIS_URL", "redis://localhost:6379")

    # Executors
    executor_enabled_openclaw: bool = os.getenv("EXECUTOR_ENABLED_OPENCLAW", "true").lower() == "true"
    executor_enabled_hermes: bool = os.getenv("EXECUTOR_ENABLED_HERMES", "true").lower() == "true"
    executor_enabled_agent_zero: bool = os.getenv("EXECUTOR_ENABLED_AGENT_ZERO", "true").lower() == "true"
    executor_check_interval: int = int(os.getenv("EXECUTOR_CHECK_INTERVAL", "5"))  # seconds

    # API
    api_token: str = os.getenv("API_TOKEN", "test-token")
    api_port: int = int(os.getenv("API_PORT", "18000"))

    # Logging
    log_level: str = os.getenv("LOG_LEVEL", "INFO")


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached singleton)."""
    return Settings()
