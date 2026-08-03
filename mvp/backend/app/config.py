import secrets

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    openai_api_key: str | None = None
    openai_model: str = "gpt-4o"
    cache_ttl_hours: int = 168
    cache_db_path: str = "cache.sqlite3"

    # Family Ancestor Tool
    family_db_path: str = "family.sqlite3"
    # Falls back to a random key if unset — fine for local dev (tokens just
    # invalidate on restart), but set a real one in .env for anything that
    # needs sessions to survive a server restart.
    jwt_secret_key: str = secrets.token_hex(32)
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24 * 30  # 30 days


settings = Settings()
