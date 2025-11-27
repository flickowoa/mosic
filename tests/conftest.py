# ruff: noqa: E402
from __future__ import annotations

from pathlib import Path
from typing import AsyncIterator
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from starlette.routing import Mount

from app.core.auth import API_KEY_HEADER_NAME
from app.core.config import settings
from app.core.db import Base, get_db, sessionmanager
from app.main import app as fastapi_app

import app.models.song  # noqa: F401
import app.models.stats  # noqa: F401


@pytest.fixture(scope="session")
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture()
async def test_engine() -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    try:
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture()
def session_factory(test_engine: AsyncEngine) -> async_sessionmaker:
    return async_sessionmaker(bind=test_engine, expire_on_commit=False)


def _update_media_mount(fastapi_app: FastAPI, directory: Path) -> None:
    for route in fastapi_app.routes:
        if isinstance(route, Mount) and route.name == "media":
            route.app.directory = str(directory)
            return


@pytest.fixture()
async def client(
    session_factory: async_sessionmaker,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setattr(sessionmanager, "init", lambda *_, **__: None)

    async def _noop_close() -> None:  # pragma: no cover - test helper
        return None

    monkeypatch.setattr(sessionmanager, "close", _noop_close)

    async def override_get_db():
        async with session_factory() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    original_media_root = settings.MEDIA_ROOT
    original_media_path = settings.media_path

    original_api_key = settings.API_KEY
    settings.API_KEY = "test-api-key"

    settings.MEDIA_ROOT = str(tmp_path / "media")
    media_path = settings.media_path
    media_path.mkdir(parents=True, exist_ok=True)
    _update_media_mount(fastapi_app, media_path)

    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={API_KEY_HEADER_NAME: settings.API_KEY},
    ) as test_client:
        yield test_client

    fastapi_app.dependency_overrides.pop(get_db, None)
    settings.MEDIA_ROOT = original_media_root
    _update_media_mount(fastapi_app, original_media_path)
    original_media_path.mkdir(parents=True, exist_ok=True)
    settings.API_KEY = original_api_key
