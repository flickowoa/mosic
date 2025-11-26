from contextlib import asynccontextmanager
import time

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.db import sessionmanager
from sqlalchemy.exc import NoResultFound
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette_exporter import PrometheusMiddleware, handle_metrics

from app.routers import play
from app.core.metrics import REQUEST_LATENCY, TOTAL_API_REQUESTS


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
app.add_middleware(
    PrometheusMiddleware,
    app_name="mosic",
    prefix="mosic",
)
app.add_route("/metrics", handle_metrics)
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


@app.middleware("http")
async def request_metrics(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    route = request.scope.get("route")
    route_path = route.path if route else request.url.path
    TOTAL_API_REQUESTS.labels(method=request.method).inc()
    REQUEST_LATENCY.labels(method=request.method, path=route_path).observe(
        time.perf_counter() - start
    )
    return response
