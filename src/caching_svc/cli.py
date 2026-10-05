import json
import sys
from contextlib import nullcontext
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Self

import httpx2
from pydantic import AfterValidator, AliasChoices, Field, HttpUrl, PositiveInt, PrivateAttr, model_validator
from pydantic_settings import BaseSettings, CliApp, SettingsConfigDict

from caching_svc.schemas import PayloadCreate

if TYPE_CHECKING:
    from typing import TextIO

STANDARD_STREAM = "-"


def read_text(source: str) -> str:
    return sys.stdin.read() if source == STANDARD_STREAM else Path(source).read_text()


def open_output(target: str) -> nullcontext[TextIO] | TextIO:
    return nullcontext(sys.stdout) if target == STANDARD_STREAM else Path(target).open("w")


class CacheCli(BaseSettings):
    model_config = SettingsConfigDict(
        cli_prog_name="cache-cli", cli_hide_none_type=True, env_prefix="CACHE_CLI_", case_sensitive=True
    )

    host: HttpUrl = Field(
        HttpUrl("http://localhost:8000"), validation_alias=AliasChoices("H", "host"), description="server URL"
    )
    repeat: PositiveInt = Field(1, validation_alias=AliasChoices("r", "repeat"), description="number of iterations")
    input: Annotated[str, AfterValidator(read_text)] | None = Field(
        None, validation_alias=AliasChoices("i", "input"), description="input JSON file, '-' for stdin"
    )
    json_payload: str | None = Field(None, validation_alias=AliasChoices("j", "json"), description="input JSON")
    output: str = Field(
        STANDARD_STREAM, validation_alias=AliasChoices("o", "output"), description="output file, '-' for stdout"
    )
    _payload: PayloadCreate = PrivateAttr()

    @model_validator(mode="after")
    def load_payload(self) -> Self:
        sources = [source for source in (self.input, self.json_payload) if source is not None]
        if len(sources) != 1:
            raise ValueError("exactly one of --input or --json is required")
        self._payload = PayloadCreate.model_validate_json(sources[0])
        return self

    def cli_cmd(self) -> None:
        with httpx2.Client(base_url=str(self.host)) as client, open_output(self.output) as output:
            for _ in range(self.repeat):
                created = client.post("/payload", json=self._payload.model_dump()).raise_for_status().json()
                read = client.get(f"/payload/{created['id']}").raise_for_status().json()
                output.write(json.dumps({"id": created["id"], **read}) + "\n")


def main() -> None:
    CliApp.run(CacheCli)
