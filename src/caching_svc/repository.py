from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.dialects import postgresql, sqlite

from caching_svc.models import Base, Payload, Transformation

if TYPE_CHECKING:
    import uuid
    from collections.abc import Callable, Collection, Mapping

    from sqlalchemy.ext.asyncio import AsyncSession

INSERTS: Mapping[str, Callable[[type[Base]], postgresql.Insert | sqlite.Insert]] = {
    "postgresql": postgresql.insert,
    "sqlite": sqlite.insert,
}


class Repository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_output(self, payload_id: uuid.UUID) -> str | None:
        return await self._session.scalar(select(Payload.output).where(Payload.id == payload_id))

    async def get_results(self, sources: Collection[str]) -> dict[str, str]:
        rows = await self._session.execute(
            select(Transformation.source, Transformation.result).where(Transformation.source.in_(sources))
        )
        return dict(rows.all())

    async def add_results(self, results: Mapping[str, str]) -> None:
        await self._insert(Transformation, [{"source": source, "result": result} for source, result in results.items()])

    async def add_payload(self, payload_id: uuid.UUID, output: str) -> None:
        await self._insert(Payload, [{"id": payload_id, "output": output}])

    async def _insert(self, model: type[Base], rows: list[dict[str, object]]) -> None:
        if rows:
            insert = INSERTS[self._session.get_bind().dialect.name]
            await self._session.execute(insert(model).values(rows).on_conflict_do_nothing())
            await self._session.commit()
