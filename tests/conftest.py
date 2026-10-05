from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from caching_svc.db import connect
from caching_svc.repository import Repository


@pytest.fixture
async def sessions(tmp_path: Path) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    async with connect(f"sqlite+aiosqlite:///{tmp_path / 'test.db'}") as sessions:
        yield sessions


@pytest.fixture
async def repository(sessions: async_sessionmaker[AsyncSession]) -> AsyncIterator[Repository]:
    async with sessions() as session:
        yield Repository(session)
