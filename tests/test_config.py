import pytest

from caching_svc.config import Settings


def test_defaults() -> None:
    settings = Settings()

    assert settings.database_url == "sqlite+aiosqlite:///cache.db"
    assert settings.transformer_latency == 0.1


def test_reads_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://user:pass@db/cache")
    monkeypatch.setenv("TRANSFORMER_LATENCY", "0")

    settings = Settings()

    assert settings.database_url == "postgresql+asyncpg://user:pass@db/cache"
    assert settings.transformer_latency == 0


def test_rejects_negative_latency() -> None:
    with pytest.raises(ValueError, match="greater than or equal to 0"):
        Settings(transformer_latency=-1)
