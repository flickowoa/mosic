from fastapi import FastAPI
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.db import sessionmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    sessionmanager.init(settings.database_url, {"echo": settings.ECHO_SQL})
    yield
    await sessionmanager.close()


app = FastAPI(lifespan=lifespan)
