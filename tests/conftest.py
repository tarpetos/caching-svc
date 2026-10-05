from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from caching_svc.api import create_app
from caching_svc.config import Settings
from caching_svc.db import connect
from caching_svc.repository import Repository
from caching_svc.service import PayloadService

LIST_1 = ["first string", "second string", "third string"]
LIST_2 = ["other string", "another string", "last string"]
PAYLOAD = {"list_1": LIST_1, "list_2": LIST_2}
OUTPUT = "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"


class CountingTransformer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    async def __call__(self, value: str) -> str:
        self.calls.append(value)
        return value.upper()


@pytest.fixture
def database_url(tmp_path: Path) -> str:
    return f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"


@pytest.fixture
async def sessions(database_url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    async with connect(database_url) as sessions:
        yield sessions


@pytest.fixture
async def repository(sessions: async_sessionmaker[AsyncSession]) -> AsyncIterator[Repository]:
    async with sessions() as session:
        yield Repository(session)


@pytest.fixture
def transformer() -> CountingTransformer:
    return CountingTransformer()


@pytest.fixture
def service(repository: Repository, transformer: CountingTransformer) -> PayloadService:
    return PayloadService(repository, transformer)


@pytest.fixture
def app(database_url: str, transformer: CountingTransformer) -> FastAPI:
    return create_app(Settings(database_url=database_url), transformer)


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app) as client:
        yield client
