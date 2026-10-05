# Caching Service

A small FastAPI microservice that builds **payloads** from two lists of strings and caches the results of an expensive
**transformer** (a stand-in for an external service), plus **`cache-cli`**, a command-line client to exercise it.

[![CI](https://github.com/tarpetos/caching-svc/actions/workflows/ci.yml/badge.svg)](https://github.com/tarpetos/caching-svc/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.14-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.142-009688)
![SQLAlchemy](https://img.shields.io/badge/SQLAlchemy-2.1-red)
![Coverage](https://img.shields.io/badge/coverage-100%25-brightgreen)

---

## Table of contents

- [Features](#features)
- [Tech stack](#tech-stack)
- [Project structure](#project-structure)
- [How it works](#how-it-works)
- [Quick start](#quick-start)
  - [Docker](#run-with-docker)
  - [Local](#run-locally)
- [Configuration](#configuration)
- [API reference](#api-reference)
- [CLI: `cache-cli`](#cli-cache-cli)
- [Development](#development)
- [Design decisions](#design-decisions)
- [Shortcuts and limitations](#shortcuts-and-limitations)

---

## Features

- `POST /payload` generates a payload and returns its identifier.
- `GET /payload/{id}` returns the generated payload.
- Every string is transformed **at most once**, ever: results are cached in the database and reused across requests.
- An identical request **reuses the existing payload identifier** and makes zero transformer calls.
- Duplicate strings inside one request are transformed once; cache misses are transformed concurrently.
- Safe under concurrent identical requests (`INSERT ... ON CONFLICT DO NOTHING`).
- SQLite by default, PostgreSQL by changing one environment variable.
- `cache-cli` built on Pydantic Settings, with validated arguments and file / stdin / stdout support.
- Dockerized, fully typed (`mypy --strict`), linted with `ruff` (`select = ["ALL"]`), **100% test coverage**.

## Tech stack

| Area          | Tool                                                       |
|---------------|------------------------------------------------------------|
| Web framework | [FastAPI](https://fastapi.tiangolo.com/) + Uvicorn         |
| Database      | SQLAlchemy 2 (async) with `aiosqlite` or `asyncpg`         |
| Validation    | Pydantic 2, Pydantic Settings (config and CLI parsing)     |
| HTTP client   | `httpx2`                                                   |
| Tooling       | [uv](https://docs.astral.sh/uv/), ruff, mypy, pytest       |
| Deployment    | Docker, Docker Compose                                     |
| CI            | GitHub Actions                                             |

## Project structure

```text
caching-svc/
├── .github/workflows/
│   └── ci.yml            # Lint and Test jobs on pull requests and pushes to master
├── src/caching_svc/
│   ├── api.py            # FastAPI app factory, routes and dependency wiring
│   ├── cli.py            # cache-cli: argument parsing and the request loop
│   ├── config.py         # service settings read from environment variables
│   ├── db.py             # engine lifecycle and table creation
│   ├── models.py         # ORM tables: transformations, payloads
│   ├── repository.py     # database access, conflict-safe inserts
│   ├── schemas.py        # request / response models shared by the API and the CLI
│   ├── service.py        # caching and payload generation logic
│   └── transformer.py    # Transformer protocol and the simulated external service
├── tests/
│   ├── conftest.py       # shared fixtures, sample data, counting transformer fake
│   ├── test_api.py       # integration: HTTP endpoints
│   ├── test_cli.py       # integration: cache-cli against the app
│   ├── test_config.py    # unit: settings
│   ├── test_repository.py
│   ├── test_service.py   # unit: caching behaviour, transformer call counts
│   └── test_transformer.py
├── compose.yaml
├── Dockerfile
├── pyproject.toml
└── uv.lock
```

## How it works

### Payload generation

Given two lists of the same length, every string is transformed and the results are interleaved:

```text
list_1: ["first string", "second string", "third string"]
list_2: ["other string", "another string", "last string"]

output: "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
```

### Request flow

```mermaid
flowchart TD
    A[POST /payload] --> B[payload id = uuid5 of the input]
    B --> C{payload exists?}
    C -- yes --> R[return id, no transformer calls]
    C -- no --> D[unique strings of both lists]
    D --> E[one SELECT for cached results]
    E --> F[transform only the misses, concurrently]
    F --> G[store new results]
    G --> H[interleave and store the payload]
    H --> R
```

### Two levels of caching

| Level           | Table             | Key                                   | Effect                                      |
|-----------------|-------------------|---------------------------------------|---------------------------------------------|
| Payload         | `payloads`        | `uuid5` of the JSON-encoded two lists | Same input returns the same id, no work     |
| Transformation  | `transformations` | the source string                     | Each string is sent to the transformer once |

The payload identifier is **deterministic**: it is derived from the input, so there is no extra hash column or lookup
table. Order matters, `["a"], ["b"]` and `["b"], ["a"]` produce different payloads.

## Quick start

### Run with Docker

```bash
docker compose up --build
```

The API is available at <http://localhost:8000>, interactive docs at <http://localhost:8000/docs>.
The SQLite database is kept in the `data` volume, so the cache survives restarts.

Build and run the image without Compose:

```bash
docker build -t caching-svc .
docker run --rm -p 8000:8000 -v caching-data:/data caching-svc
```

### Run locally

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/) (it installs Python 3.14 if needed).

```bash
uv sync
uv run uvicorn caching_svc.api:app --reload
```

## Configuration

The service reads its settings from environment variables. Both have defaults, so nothing needs to be set to run it.

| Variable              | Default                         | Description                                          |
|-----------------------|---------------------------------|------------------------------------------------------|
| `DATABASE_URL`        | `sqlite+aiosqlite:///cache.db`  | SQLAlchemy async URL                                 |
| `TRANSFORMER_LATENCY` | `0.1`                           | Simulated transformer delay in seconds, must be ≥ 0  |

The container runs in `/data`, so the default SQLite file is `/data/cache.db`, inside the `data` volume.

### Using PostgreSQL

The `asyncpg` driver is already installed, so only the URL changes:

```bash
DATABASE_URL=postgresql+asyncpg://user:password@host:5432/cache docker compose up --build
```

Tables are created automatically on startup.

## API reference

### `POST /payload`

Creates a payload, or returns the identifier of an identical existing one.

```bash
curl -X POST http://localhost:8000/payload \
  -H "Content-Type: application/json" \
  -d '{
        "list_1": ["first string", "second string", "third string"],
        "list_2": ["other string", "another string", "last string"]
      }'
```

**`201 Created`**

```json
{
  "id": "60f1257e-813f-5419-a7cc-4c72ffdbd8d1",
  "message": "Payload created"
}
```

Validation rules: both lists are required, non-empty, contain only strings and have the same length.

**`422 Unprocessable Content`**

```json
{
  "detail": [
    {
      "type": "value_error",
      "loc": ["body"],
      "msg": "Value error, list_1 and list_2 must have the same length",
      "input": {"list_1": ["a"], "list_2": ["b", "c"]},
      "ctx": {"error": {}}
    }
  ]
}
```

### `GET /payload/{id}`

Returns the generated payload.

```bash
curl http://localhost:8000/payload/60f1257e-813f-5419-a7cc-4c72ffdbd8d1
```

**`200 OK`**

```json
{
  "output": "FIRST STRING, OTHER STRING, SECOND STRING, ANOTHER STRING, THIRD STRING, LAST STRING"
}
```

| Status | When                          |
|--------|-------------------------------|
| `200`  | Payload found                 |
| `404`  | `{"detail": "Payload not found"}` |
| `422`  | The id is not a valid UUID    |

## CLI: `cache-cli`

`cache-cli` sends a payload to the service, reads it back and writes the result. It is installed with the project
(`uv sync`) and is meant for testing the service from scripts or the terminal.

```text
usage: cache-cli [-h] [-H HttpUrl] [-r int] [-i str] [-j str] [-o str]
```

| Option              | Default                  | Description                                  |
|---------------------|--------------------------|----------------------------------------------|
| `-H`, `--host URL`  | `http://localhost:8000/` | Service URL                                  |
| `-r`, `--repeat N`  | `1`                      | Number of iterations, must be > 0            |
| `-i`, `--input FILE`| —                        | JSON input file, `-` reads from stdin        |
| `-j`, `--json JSON` | —                        | JSON input passed inline                     |
| `-o`, `--output FILE` | `-`                    | Output file, `-` writes to stdout            |
| `-h`, `--help`      |                          | Show help and exit                           |

Exactly one of `--input` and `--json` is required. The input is validated with the same schema as the API before any
request is sent.

Each iteration runs `POST /payload` followed by `GET /payload/{id}` and writes one JSON line:

```json
{"id": "60f1257e-813f-5419-a7cc-4c72ffdbd8d1", "output": "FIRST STRING, OTHER STRING, ..."}
```

### Examples

Inline JSON, printed to stdout:

```bash
uv run cache-cli -j '{"list_1": ["first string"], "list_2": ["other string"]}'
```

From a file, three iterations, saved to a file:

```bash
uv run cache-cli -H http://localhost:8000 -i payload.json -r 3 -o results.jsonl
```

From stdin:

```bash
echo '{"list_1": ["a", "b"], "list_2": ["c", "d"]}' | uv run cache-cli -i -
```

Invalid arguments fail before any request with a Pydantic validation error, for example
`exactly one of --input or --json is required` or `Input should be greater than 0`.

## Development

```bash
uv sync                                              # install runtime and dev dependencies
uv run pytest                                        # run tests, fails below 100% coverage
uv run ruff check .                                  # lint
uv run ruff format . --line-length=120               # format sources
uv run ruff format tests --line-length=120           # format tests (excluded from the default ruff run)
uv run mypy src tests                                # strict type check
```

### Tests

| Kind        | File                  | What it covers                                                         |
|-------------|-----------------------|------------------------------------------------------------------------|
| Unit        | `test_config.py`      | defaults, environment overrides, validation                            |
| Unit        | `test_transformer.py` | uppercase result and simulated latency                                 |
| Unit        | `test_repository.py`  | persistence, duplicate inserts ignored, cache lookups                  |
| Unit        | `test_service.py`     | output format, id reuse, transformer called only for uncached strings |
| Integration | `test_api.py`         | full HTTP flow, status codes, validation errors                        |
| Integration | `test_cli.py`         | real `main()` against the app: stdin, files, repeat, invalid arguments |

Every test gets its own temporary SQLite database. A `CountingTransformer` fake records calls, so tests assert exactly
how many times the "external service" was hit. Pytest treats every warning as an error.

### Continuous integration

[`.github/workflows/ci.yml`](.github/workflows/ci.yml) runs on every pull request and on pushes to `master`, so a
commit on a pull request branch is checked once, not twice. It has two independent jobs, so a lint failure and a test
failure are reported separately:

| Job    | Commands                                                                   |
|--------|----------------------------------------------------------------------------|
| `Lint` | `ruff check`, `ruff format --check` (sources and tests), `mypy src tests`  |
| `Test` | `pytest` with the 100% coverage gate                                       |

Both jobs install the exact locked dependencies (`uv sync --locked`). To block merging until they pass, open
**Settings → Branches → Branch protection rules** (or **Rules → Rulesets**) for `master`, enable
**Require status checks to pass before merging** and select `Lint` and `Test`.

## Design decisions

- **Layers with single responsibilities.** `api` handles HTTP, `service` holds the caching logic, `repository` talks to
  the database, `transformer` simulates the external service.
- **Dependency inversion.** `PayloadService` receives its repository and a `Transformer` protocol, so the real
  external service can replace `UppercaseTransformer` without touching the logic. `create_app` takes the transformer as
  an argument for the same reason, which is how tests inject the counting fake.
- **One schema, two consumers.** The CLI validates input with the API's `PayloadCreate` model, so the rules live in one
  place.
- **Concurrency safety without locks.** Inserts use `ON CONFLICT DO NOTHING` (SQLite and PostgreSQL dialects), so two
  identical requests racing each other never fail.
- **Deterministic ids.** `uuid5` of the input turns "reuse the identifier" into a primary-key lookup.

## Shortcuts and limitations

| Shortcut                                        | Reason                                                       |
|-------------------------------------------------|--------------------------------------------------------------|
| Tables created on startup, no Alembic migrations | Two simple tables; migrations add setup without value here  |
| The transformer is `str.upper()` with a delay   | Simulates the external service described in the task         |
| Source strings are the cache primary key        | Simplest key; very long strings would need a hash key on PostgreSQL |
| Concurrent requests may transform the same new string twice | Results are idempotent; avoiding it needs cross-request locking |
| No authentication, rate limiting or input size limits | Out of scope for the task                                |
| No container healthcheck                        | The slim image has no `curl`; a healthcheck needs an extra endpoint or package |
| A missing `--input` file raises `FileNotFoundError` | The message already names the file                       |
