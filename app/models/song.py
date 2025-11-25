from uuid import uuid4
from typing import Sequence

from sqlalchemy import String, select, Integer
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

from pydantic import BaseModel, ConfigDict


class SongCreateError(RuntimeError):
    """Raised when persisting a Song fails."""


class Song(Base):
    __tablename__ = "songs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid4())
    )
    title: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(String, nullable=True)
    duration: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_url: Mapped[str] = mapped_column(String, nullable=False)

    @classmethod
    async def get_by_id(cls, session: AsyncSession, song_id: str) -> "Song":
        stmt = select(cls).where(cls.id == song_id)
        result = await session.execute(stmt)
        song = result.scalar_one_or_none()
        if song is None:
            raise NoResultFound(f"Song with id {song_id} not found")
        return song

    @classmethod
    async def list_all(cls, session: AsyncSession) -> Sequence["Song"]:
        stmt = select(cls)
        result = await session.execute(stmt)
        songs = list(result.scalars().all())
        return songs

    @classmethod
    async def create(
        cls,
        session: AsyncSession,
        title: str,
        description: str | None,
        duration: int,
        audio_url: str,
    ) -> "Song":
        song = cls(
            title=title, description=description, duration=duration, audio_url=audio_url
        )
        session.add(song)
        try:
            await session.commit()
        except IntegrityError as exc:
            await session.rollback()
            raise SongCreateError("Failed to persist song") from exc
        except Exception:
            await session.rollback()
            raise
        await session.refresh(song)
        return song


# FASTAPI VIEWS


class SongBase(BaseModel):
    title: str
    description: str | None = None
    duration: int
    audio_url: str


class SongCreate(SongBase):
    pass


class SongRead(SongBase):
    id: str
    model_config = ConfigDict(from_attributes=True)
