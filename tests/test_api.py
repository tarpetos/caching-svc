import uuid
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi import status
from fastapi.testclient import TestClient

from caching_svc.api import create_app
from caching_svc.config import Settings
from tests.conftest import CountingTransformer

PAYLOAD = {
    "list_1": ["first string", "second string", "third string"],
    "list_2": ["other string", "another string", "last string"],
}


@pytest.fixture
def client(tmp_path: Path, transformer: CountingTransformer) -> Iterator[TestClient]:
    settings = Settings(_env_file=None, database_url=f"sqlite+aiosqlite:///{tmp_path / 'api.db'}")
    with TestClient(create_app(settings, transformer)) as client:
        yield client


def test_create_and_read_payload(client: TestClient) -> None:
    created = client.post("/payload", json=PAYLOAD)

    assert created.status_code == status.HTTP_201_CREATED
    assert created.json()["message"] == "Payload created"

    read = client.get(f"/payload/{created.json()['id']}")

    assert read.status_code == status.HTTP_200_OK
    assert read.json() == {
        "output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
    }


def test_create_reuses_identifier(client: TestClient, transformer: CountingTransformer) -> None:
    first = client.post("/payload", json=PAYLOAD).json()["id"]
    transformer.calls.clear()

    assert client.post("/payload", json=PAYLOAD).json()["id"] == first
    assert transformer.calls == []


@pytest.mark.parametrize(
    "body",
    [
        {"list_1": ["a"], "list_2": ["b", "c"]},
        {"list_1": [], "list_2": []},
        {"list_1": ["a"]},
        {"list_1": ["a"], "list_2": [1]},
    ],
)
def test_create_rejects_invalid_input(client: TestClient, body: dict[str, object]) -> None:
    assert client.post("/payload", json=body).status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


def test_read_unknown_payload(client: TestClient) -> None:
    response = client.get(f"/payload/{uuid.uuid4()}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": "Payload not found"}


def test_read_rejects_invalid_identifier(client: TestClient) -> None:
    assert client.get("/payload/not-a-uuid").status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
