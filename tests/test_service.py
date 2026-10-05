import uuid

from caching_svc.service import PayloadService
from tests.conftest import LIST_1, LIST_2, OUTPUT, CountingTransformer


async def test_create_interleaves_transformed_strings(service: PayloadService) -> None:
    payload_id = await service.create(LIST_1, LIST_2)

    assert await service.read(payload_id) == OUTPUT


async def test_create_reuses_identifier_without_transforming(
    service: PayloadService, transformer: CountingTransformer
) -> None:
    payload_id = await service.create(LIST_1, LIST_2)
    transformer.calls.clear()

    assert await service.create(LIST_1, LIST_2) == payload_id
    assert transformer.calls == []


async def test_create_transforms_only_uncached_strings(
    service: PayloadService, transformer: CountingTransformer
) -> None:
    await service.create(["a", "b"], ["c", "d"])
    transformer.calls.clear()

    await service.create(["a", "e"], ["c", "d"])

    assert transformer.calls == ["e"]


async def test_create_transforms_duplicates_once(service: PayloadService, transformer: CountingTransformer) -> None:
    payload_id = await service.create(["a", "a"], ["a", "b"])

    assert sorted(transformer.calls) == ["a", "b"]
    assert await service.read(payload_id) == "A, A, A, B"


async def test_create_distinguishes_order(service: PayloadService) -> None:
    assert await service.create(["a"], ["b"]) != await service.create(["b"], ["a"])


async def test_read_unknown_payload(service: PayloadService) -> None:
    assert await service.read(uuid.uuid4()) is None
