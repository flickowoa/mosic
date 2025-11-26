from pathlib import Path
import mimetypes
import logging

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.config import settings
from app.models.song import Song, SongCreateError
from app.models.stats import PlayCount
from app.core.media import (
    extract_audio_metadata,
    store_audio_file,
    UploadTooLargeError,
)
from app.core.metrics import STREAMS_BY_CLIP

router = APIRouter(prefix="/play", tags=["play"])
ALLOWED_AUDIO_TYPES = {mime.lower() for mime in settings.ALLOWED_AUDIO_MIME_TYPES}
logger = logging.getLogger(__name__)


@router.get("/")
async def list_songs(db: AsyncSession = Depends(get_db)):
    songs = await Song.list_all(db)
    return songs


@router.get("/{song_id}/stats")
async def get_song_stats(song_id: str, db: AsyncSession = Depends(get_db)):
    await Song.get_by_id(db, song_id)
    playcount = await PlayCount.get_by_id(db, song_id)
    return playcount


@router.post("/")
async def create_song(
    title: str,
    description: str | None,
    duration: int,
    audio_url: str,
    db: AsyncSession = Depends(get_db),
):
    song = await Song.create(db, title, description, duration, audio_url)
    return song


def _build_audio_url(filename: str) -> str:
    return f"{settings.media_url_path}/{filename}"


@router.post("/upload")
async def upload_song(
    file: UploadFile = File(...),
    title: str | None = Form(None),
    description: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    content_type = (file.content_type or "").lower()
    if content_type not in ALLOWED_AUDIO_TYPES:
        raise HTTPException(status_code=415, detail="Unsupported audio content type")

    try:
        saved_path = await store_audio_file(
            file,
            settings.media_path,
            max_bytes=settings.max_upload_bytes,
        )
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc

    try:
        metadata = await run_in_threadpool(extract_audio_metadata, saved_path)

        inferred_title = (
            metadata.title or title or Path(file.filename or saved_path.name).stem
        )
        inferred_description = description or metadata.description
        duration = metadata.duration_seconds or 0
        audio_url = _build_audio_url(saved_path.name)

        song = await Song.create(
            db,
            title=inferred_title,
            description=inferred_description,
            duration=duration,
            audio_url=audio_url,
        )
    except SongCreateError as exc:
        saved_path.unlink(missing_ok=True)
        logger.exception("Song persistence failed for %s", saved_path)
        raise HTTPException(status_code=409, detail="Song already exists") from exc
    except Exception as exc:  # pragma: no cover - safeguards tests
        saved_path.unlink(missing_ok=True)
        logger.exception("Unhandled upload failure for %s", saved_path)
        raise HTTPException(
            status_code=500, detail="Failed to save song metadata"
        ) from exc

    return song


@router.get("/{song_id}/stream")
async def stream_song(song_id: str, db: AsyncSession = Depends(get_db)):
    song = await Song.get_by_id(db, song_id)
    file_path = settings.media_path / Path(song.audio_url).name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    playcount = await PlayCount.increment_count(db, song_id)
    STREAMS_BY_CLIP.labels(song_id=song_id, title=song.title).set(playcount)

    media_type, _ = mimetypes.guess_type(file_path.name)

    def iterfile():
        with file_path.open("rb") as f:
            while chunk := f.read(1024 * 1024):
                yield chunk

    return StreamingResponse(
        iterfile(),
        media_type=media_type or "music/mpeg",
    )
