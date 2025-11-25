from sqlmodel import SQLModel, create_engine
from app.core.config import settings

engine = create_engine("sqlite:///./mosic.db", echo=True)


def init_db():
    SQLModel.metadata.create_all(engine)
