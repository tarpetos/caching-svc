import asyncio
import json
import uuid
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

    from caching_svc.repository import Repository
    from caching_svc.transformer import Transformer


class PayloadService:
    def __init__(self, repository: Repository, transformer: Transformer) -> None:
        self._repository = repository
        self._transformer = transformer

    async def create(self, list_1: Sequence[str], list_2: Sequence[str]) -> uuid.UUID:
        payload_id = uuid.uuid5(uuid.NAMESPACE_OID, json.dumps([list_1, list_2]))
        if await self._repository.get_output(payload_id) is None:
            results = await self._transform({*list_1, *list_2})
            output = ", ".join(results[value] for pair in zip(list_1, list_2, strict=True) for value in pair)
            await self._repository.add_payload(payload_id, output)
        return payload_id

    async def read(self, payload_id: uuid.UUID) -> str | None:
        return await self._repository.get_output(payload_id)

    async def _transform(self, values: set[str]) -> dict[str, str]:
        cached = await self._repository.get_results(values)
        missing = list(values - cached.keys())
        fresh = dict(zip(missing, await asyncio.gather(*map(self._transformer, missing)), strict=True))
        await self._repository.add_results(fresh)
        return cached | fresh
