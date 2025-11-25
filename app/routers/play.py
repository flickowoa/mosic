from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import NoResultFound
from fastapi.responses import StreamingResponse

from app.core.db import get_db
from app.core.config import settings
from app.models.song import Song
from app.models.stats import PlayCount
from app.core.media import extract_audio_metadata, store_audio_file

router = APIRouter(prefix="/play", tags=["play"])


@router.get("/")
async def list_songs(request: Request, db: AsyncSession = Depends(get_db)):
    songs = await Song.list_all(db)
    return songs


@router.get("/{song_id}/stats")
async def get_song_stats(song_id: str, db: AsyncSession = Depends(get_db)):
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
    saved_path = await store_audio_file(file, settings.media_path)
    metadata = extract_audio_metadata(saved_path)

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
    return song


@router.get("/{song_id}/stream")
async def stream_song(song_id: str, db: AsyncSession = Depends(get_db)):
    song = await Song.get_by_id(db, song_id)
    file_path = settings.media_path / Path(song.audio_url).name

    await PlayCount.increment_count(db, song_id)

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found")

    def iterfile():
        with file_path.open("rb") as f:
            while chunk := f.read(1024 * 1024):
                yield chunk

    return StreamingResponse(iterfile(), media_type="audio/mpeg")
