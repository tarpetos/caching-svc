from pydantic import NonNegativeFloat
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    database_url: str = "sqlite+aiosqlite:///cache.db"
    transformer_latency: NonNegativeFloat = 0.1
