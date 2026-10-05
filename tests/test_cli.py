import io
import json
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from caching_svc.cli import main
from tests.conftest import OUTPUT, PAYLOAD

HOST = "http://cache.test/"


@pytest.fixture(autouse=True)
def server(monkeypatch: pytest.MonkeyPatch, app: FastAPI) -> None:
    monkeypatch.setattr("httpx2.Client", lambda base_url: TestClient(app, base_url=base_url))


def run(monkeypatch: pytest.MonkeyPatch, *args: str) -> None:
    monkeypatch.setattr(sys, "argv", ["cache-cli", "-H", HOST, *args])
    main()


def read_lines(text: str) -> list[dict[str, str]]:
    return [json.loads(line) for line in text.splitlines()]


def test_repeats_json_input_to_stdout(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    run(monkeypatch, "--json", json.dumps(PAYLOAD), "--repeat", "2")

    first, second = read_lines(capsys.readouterr().out)
    assert first == second
    assert first["output"] == OUTPUT


def test_reads_input_file_and_writes_output_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    source, target = tmp_path / "input.json", tmp_path / "output.jsonl"
    source.write_text(json.dumps(PAYLOAD))

    run(monkeypatch, "-i", str(source), "-o", str(target))

    assert [line["output"] for line in read_lines(target.read_text())] == [OUTPUT]


def test_reads_input_from_stdin(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(PAYLOAD)))

    run(monkeypatch, "-i", "-")

    assert [line["output"] for line in read_lines(capsys.readouterr().out)] == [OUTPUT]


@pytest.mark.parametrize(
    ("args", "error"),
    [
        ((), "exactly one of --input or --json is required"),
        (("-i", "-", "-j", json.dumps(PAYLOAD)), "exactly one of --input or --json is required"),
        (("-j", '{"list_1": ["a"], "list_2": []}'), "List should have at least 1 item"),
        (("-j", "not json"), "Invalid JSON"),
        (("-j", json.dumps(PAYLOAD), "-r", "0"), "Input should be greater than 0"),
        (("-j", json.dumps(PAYLOAD), "-H", "not-a-url"), "Input should be a valid URL"),
    ],
)
def test_rejects_invalid_arguments(monkeypatch: pytest.MonkeyPatch, args: tuple[str, ...], error: str) -> None:
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(PAYLOAD)))

    with pytest.raises(ValidationError, match=error):
        run(monkeypatch, *args)
