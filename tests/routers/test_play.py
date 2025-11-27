from __future__ import annotations

import mimetypes
from pathlib import Path

import pytest

from app.core.auth import API_KEY_HEADER_NAME
from app.core.config import settings
from app.models.song import Song
from app.models.stats import PlayCount


def _media_contents() -> list[Path]:
    return [p for p in settings.media_path.glob("*") if p.is_file()]


@pytest.mark.anyio
async def test_invalid_api_key_rejected(client):
    response = await client.get("/play/", headers={API_KEY_HEADER_NAME: "bad"})
    assert response.status_code == 401


@pytest.mark.anyio
async def test_list_songs_returns_persisted_entries(client, session_factory):
    async with session_factory() as session:
        first = Song(
            id="song-1",
            title="First",
            description="Desc",
            duration=10,
            audio_url="/media/first.mp3",
        )
        second = Song(
            id="song-2",
            title="Second",
            description=None,
            duration=20,
            audio_url="/media/second.mp3",
        )
        session.add_all([first, second])
        await session.commit()

    response = await client.get("/play/")
    assert response.status_code == 200
    payload = response.json()
    assert {song["id"] for song in payload} == {"song-1", "song-2"}


@pytest.mark.anyio
async def test_get_song_stats_requires_existing_song(client):
    response = await client.get("/play/nonexistent/stats")
    assert response.status_code == 404


@pytest.mark.anyio
async def test_get_song_stats_returns_playcount(client, session_factory):
    song_id = "stats-song"

    async with session_factory() as session:
        song = Song(
            id=song_id,
            title="Stats",
            description=None,
            duration=5,
            audio_url="/media/stats.mp3",
        )
        session.add(song)
        await session.commit()

    response = await client.get(f"/play/{song_id}/stats")
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == song_id
    assert payload["count"] == 0


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
