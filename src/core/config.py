"""
src/core/config.py
Centralised settings — OpenRouter + MySQL edition.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── OpenRouter ────────────────────────────────────────────────────────────
    openrouter_api_key: str = ""
    openrouter_model: str = "openai/gpt-4o-mini"
    openrouter_site_url: str = "http://localhost:8000"
    openrouter_site_name: str = "HRMS-LLM-SQL"

    # OpenRouter base URL — do NOT change this
    openrouter_base_url: str = "https://openrouter.ai/api/v1"

    # ── MySQL ─────────────────────────────────────────────────────────────────
    mysql_host: str = "3.7.213.254"
    mysql_port: int = 3306
    mysql_user: str = "root"
    mysql_password: str = ""
    mysql_db: str = "development"

    # ── App ───────────────────────────────────────────────────────────────────
    app_env: str = "development"
    log_level: str = "INFO"
    query_cache_ttl: int = 300
    max_rows: int = 100
    allowed_origins: str = "http://localhost:3000"

    @property
    def database_url(self) -> str:
        from urllib.parse import quote_plus
        pw = quote_plus(self.mysql_password)   # safely encode ! @ # $ etc.
        return (
            f"mysql+pymysql://{self.mysql_user}:{pw}"
            f"@{self.mysql_host}:{self.mysql_port}"
            f"/{self.mysql_db}?charset=utf8mb4"
        )

    @property
    def origins_list(self) -> list[str]:
        return [o.strip() for o in self.allowed_origins.split(",")]


@lru_cache
def get_settings() -> Settings:
    return Settings()