from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="GTM_", env_file=".env", extra="ignore")

    api_token: str = "local-demo-token"
    webhook_secret: str = "local-webhook-secret"
    database_path: Path = Path("data/gtm_workflows.db")
    knowledge_path: Path = Path("sample_data/knowledge")
    replay_path: Path = Path("sample_data/replay_responses.json")
    max_attempts: int = 3
    retry_delay_seconds: float = 0.05
    allowed_origins: str = "http://localhost:5173"


@lru_cache
def get_settings() -> Settings:
    return Settings()

