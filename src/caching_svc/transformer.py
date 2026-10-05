import asyncio
from dataclasses import dataclass
from typing import Protocol


class Transformer(Protocol):
    async def __call__(self, value: str) -> str: ...


@dataclass(frozen=True)
class UppercaseTransformer:
    latency: float

    async def __call__(self, value: str) -> str:
        await asyncio.sleep(self.latency)
        return value.upper()
