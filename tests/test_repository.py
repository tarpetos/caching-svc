import uuid

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from caching_svc.repository import Repository


async def test_get_output_of_unknown_payload(repository: Repository) -> None:
    assert await repository.get_output(uuid.uuid4()) is None


async def test_add_payload_persists_and_ignores_duplicates(
    repository: Repository, sessions: async_sessionmaker[AsyncSession]
) -> None:
    payload_id = uuid.uuid4()

    await repository.add_payload(payload_id, "A, B")
    await repository.add_payload(payload_id, "C, D")

    async with sessions() as session:
        assert await Repository(session).get_output(payload_id) == "A, B"


async def test_get_results_returns_only_cached(repository: Repository) -> None:
    await repository.add_results({"a": "A", "b": "B"})

    assert await repository.get_results({"a", "c"}) == {"a": "A"}


async def test_add_results_persists_and_ignores_duplicates(
    repository: Repository, sessions: async_sessionmaker[AsyncSession]
) -> None:
    await repository.add_results({"a": "A"})
    await repository.add_results({"a": "X", "b": "B"})
    await repository.add_results({})

    async with sessions() as session:
        assert await Repository(session).get_results({"a", "b"}) == {"a": "A", "b": "B"}
