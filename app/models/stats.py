from sqlalchemy import String, select, Integer
from sqlalchemy.exc import IntegrityError, NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

from pydantic import BaseModel, ConfigDict

from app.core.metrics import STREAMS_BY_CLIP


class PlayCount(Base):
    __tablename__ = "play_counts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    @classmethod
    async def get_by_id(cls, session: AsyncSession, playcount_id: str) -> "PlayCount":
        stmt = select(cls).where(cls.id == playcount_id)
        result = await session.execute(stmt)
        playcount = result.scalar_one_or_none()
        if playcount is None:
            playcount = cls(id=playcount_id, count=0)
            session.add(playcount)
            await session.commit()
            await session.refresh(playcount)
        return playcount

    @classmethod
    async def increment_count(
        cls, session: AsyncSession, playcount_id: str, song_title: str
    ) -> int:
        stmt = select(cls).where(cls.id == playcount_id).with_for_update()
        result = await session.execute(stmt)
        playcount = result.scalar_one_or_none()

        if playcount is None:
            playcount = cls(id=playcount_id, count=1)
            session.add(playcount)
        else:
            playcount.count += 1
            session.add(playcount)

        current_count = playcount.count

        await session.commit()

        STREAMS_BY_CLIP.labels(song_id=playcount_id, title=song_title).set(
            current_count
        )


# FASTAPI VIEWS


class PlayCountBase(BaseModel):
    count: int


class PlayCountRead(PlayCountBase):
    id: str
    model_config = ConfigDict(from_attributes=True)
