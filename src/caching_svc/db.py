from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from caching_svc.models import Base

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


@asynccontextmanager
async def connect(url: str) -> AsyncIterator[async_sessionmaker[AsyncSession]]:
    engine = create_async_engine(url)
    try:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        yield async_sessionmaker(engine, expire_on_commit=False)
    finally:
        await engine.dispose()
