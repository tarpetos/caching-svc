from unittest.mock import AsyncMock

import pytest

from caching_svc.transformer import UppercaseTransformer


async def test_uppercases_after_latency(monkeypatch: pytest.MonkeyPatch) -> None:
    sleep = AsyncMock()
    monkeypatch.setattr("asyncio.sleep", sleep)

    assert await UppercaseTransformer(latency=0.5)("first string") == "FIRST STRING"
    sleep.assert_awaited_once_with(0.5)
