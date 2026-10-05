import uuid
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated

from fastapi import APIRouter, Depends, FastAPI, HTTPException, Request, status

from caching_svc.config import Settings
from caching_svc.db import connect
from caching_svc.repository import Repository
from caching_svc.schemas import PayloadCreate, PayloadCreated, PayloadRead
from caching_svc.service import PayloadService
from caching_svc.transformer import Transformer, UppercaseTransformer

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


async def get_service(request: Request) -> AsyncIterator[PayloadService]:
    async with request.app.state.sessions() as session:
        yield PayloadService(Repository(session), request.app.state.transformer)


Service = Annotated[PayloadService, Depends(get_service)]
router = APIRouter(prefix="/payload")


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_payload(payload: PayloadCreate, service: Service) -> PayloadCreated:
    return PayloadCreated(id=await service.create(payload.list_1, payload.list_2))


@router.get("/{payload_id}")
async def read_payload(payload_id: uuid.UUID, service: Service) -> PayloadRead:
    output = await service.read(payload_id)
    if output is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Payload not found")
    return PayloadRead(output=output)


def create_app(settings: Settings, transformer: Transformer) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        async with connect(settings.database_url) as sessions:
            app.state.sessions = sessions
            yield

    app = FastAPI(title="Caching Service", lifespan=lifespan)
    app.state.transformer = transformer
    app.include_router(router)
    return app


settings = Settings()
app = create_app(settings, UppercaseTransformer(settings.transformer_latency))
