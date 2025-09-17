# app/settings.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    database_url: str
    allowed_origins: List[str] = ["http://localhost:8501"]
    openai_api_key: str
    embedding_model: str = "text-embedding-3-small"
    log_level: str = "info"  # ← 추가

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # ← 여분 키가 있어도 무시(선택, 안전장치)
    )

settings = Settings()
