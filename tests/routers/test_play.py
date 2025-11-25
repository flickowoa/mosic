from __future__ import annotations

import mimetypes
from pathlib import Path

import pytest

from app.core.config import settings
from app.models.song import Song
from app.models.stats import PlayCount


def _media_contents() -> list[Path]:
    return [p for p in settings.media_path.glob("*") if p.is_file()]


@pytest.mark.anyio
async def test_get_song_stats_requires_existing_song(client):
    response = await client.get("/play/nonexistent/stats")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_upload_rejects_unsupported_audio_type(client):
    response = await client.post(
        "/play/upload",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 415


@pytest.mark.anyio
async def test_upload_rejects_file_exceeding_limit(
    client, monkeypatch: pytest.MonkeyPatch
):
    monkeypatch.setattr(settings, "MAX_UPLOAD_MB", 1)
    oversize = b"0" * (settings.max_upload_bytes + 1)

    response = await client.post(
        "/play/upload",
        files={"file": ("big.mp3", oversize, "audio/mpeg")},
    )

    assert response.status_code == 413


@pytest.mark.anyio
async def test_upload_cleans_up_file_on_database_failure(
    client, monkeypatch: pytest.MonkeyPatch
):
    async def failing_create(*_args, **_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(Song, "create", failing_create)

    response = await client.post(
        "/play/upload",
        files={"file": ("track.mp3", b"abc", "audio/mpeg")},
    )

    assert response.status_code == 500
    assert _media_contents() == []


@pytest.mark.anyio
async def test_stream_song_serves_file_and_increments_playcount(
    client, session_factory
):
    for existing in _media_contents():
        existing.unlink()

    song_id = "streamable"
    media_file = settings.media_path / "stream.mp3"
    payload = b"binary audio data"
    media_file.write_bytes(payload)

    async with session_factory() as session:
        song = Song(
            id=song_id,
            title="Test",
            description=None,
            duration=1,
            audio_url=f"{settings.media_url_path}/{media_file.name}",
        )
        session.add(song)
        await session.commit()

    response = await client.get(f"/play/{song_id}/stream")

    assert response.status_code == 200
    assert response.content == payload
    expected_mime, _ = mimetypes.guess_type(media_file.name)
    assert response.headers["content-type"] == (
        expected_mime or "application/octet-stream"
    )

    async with session_factory() as session:
        playcount = await PlayCount.get_by_id(session, song_id)
        assert playcount.count == 1
