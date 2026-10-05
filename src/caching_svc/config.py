from pydantic import NonNegativeFloat
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///cache.db"
    transformer_latency: NonNegativeFloat = 0.1
