"""Application settings, read from environment variables (see .env.example).

This is the only module that reads configuration; other code receives a Settings object.
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LKD_",
        env_file=("../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    env: Literal["development", "test", "staging", "production"] = "development"
    base_url: str = "http://localhost:5173"
    secret_key: SecretStr = SecretStr("change-me-local-only")
    database_url: str = "postgresql+psycopg://lokdhara:lokdhara@localhost:5432/lokdhara"
    log_level: str = "INFO"
    worker_poll_seconds: float = Field(default=5.0, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
