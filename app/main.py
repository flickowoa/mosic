from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.db import sessionmanager
from sqlalchemy.exc import NoResultFound
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import play


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Initializing session manager")
    sessionmanager.init(settings.database_url, {"echo": settings.ECHO_SQL})
    yield
    print("Closing session manager")
    await sessionmanager.close()
    print("Session manager closed")


settings.media_path.mkdir(parents=True, exist_ok=True)

app = FastAPI(lifespan=lifespan)
app.mount(
    settings.media_url_path,
    StaticFiles(directory=str(settings.media_path)),
    name="media",
)
app.include_router(play.router)


@app.exception_handler(NoResultFound)
async def validation_exception_handler(request, exc):
    return JSONResponse({"detail": str(exc)}, status_code=404)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse({"detail": str(exc.detail)}, status_code=exc.status_code)
