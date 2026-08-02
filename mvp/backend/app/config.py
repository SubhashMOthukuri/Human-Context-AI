from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    cache_ttl_hours: int = 168
    cache_db_path: str = "cache.sqlite3"


settings = Settings()
