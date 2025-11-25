from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from uuid import uuid4

from fastapi import UploadFile
from fastapi.concurrency import run_in_threadpool
from mutagen._file import File
from mutagen._util import MutagenError

_CHUNK_SIZE = 1024 * 1024  # 1 MiB


class UploadTooLargeError(ValueError):
    """Raised when an uploaded file exceeds the configured size limit."""

    pass


@dataclass(slots=True)
class AudioMetadata:
    title: str | None = None
    description: str | None = None
    duration_seconds: int | None = None


async def store_audio_file(
    upload: UploadFile, media_root: Path, *, max_bytes: int | None = None
) -> Path:
    """Persist an uploaded audio file to disk and return its path."""

    media_root.mkdir(parents=True, exist_ok=True)
    suffix = Path(upload.filename or "").suffix or ""
    filename = f"{uuid4().hex}{suffix}"
    destination = media_root / filename

    await upload.seek(0)

    def _copy_to_disk() -> None:
        written = 0
        with destination.open("wb") as buffer:
            while True:
                chunk = upload.file.read(_CHUNK_SIZE)
                if not chunk:
                    break
                written += len(chunk)
                if max_bytes is not None and written > max_bytes:
                    raise UploadTooLargeError("Uploaded file exceeds allowed size")
                buffer.write(chunk)

    try:
        await run_in_threadpool(_copy_to_disk)
    except UploadTooLargeError:
        destination.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()

    return destination


def extract_audio_metadata(file_path: Path) -> AudioMetadata:
    """Read common metadata values from an audio file."""

    metadata = AudioMetadata()

    try:
        audio = File(file_path)
    except (MutagenError, OSError):
        return metadata

    if audio is None:
        return metadata

    info = getattr(audio, "info", None)
    length = getattr(info, "length", None)
    if length:
        metadata.duration_seconds = int(round(length))

    tags = getattr(audio, "tags", None)
    if tags and hasattr(tags, "get"):
        metadata.title = _first_tag_value(tags, ("TIT2", "title", "\xa9nam", "Title"))
        metadata.description = _first_tag_value(
            tags, ("COMM::'eng'", "COMM", "comment", "description", "\xa9cmt")
        )

    return metadata


def _first_tag_value(tags: dict, keys: Iterable[str]) -> str | None:
    for key in keys:
        value = tags.get(key)
        if value is None:
            continue
        text = _tag_value_to_string(value)
        if text:
            return text
    return None


def _tag_value_to_string(value: object) -> str | None:
    candidate = value
    if isinstance(candidate, (list, tuple)):
        candidate = candidate[0] if candidate else None
    if candidate is None:
        return None
    try:
        text = str(candidate).strip()
    except Exception:  # pragma: no cover - best effort
        return None
    return text or None
