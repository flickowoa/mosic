from pathlib import Path

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="MOSIC_"
    )
    APP_NAME: str = "Mosic"
    APP_PORT: int = 8000

    DB_HOST: str = "db"
    DB_PORT: int = 5432
    DB_NAME: str = "mosic"
    DB_USER: str = "mosic"
    DB_PASSWORD: str = "mosicpassword"
    ECHO_SQL: bool = False
    MEDIA_ROOT: str = "media"
    MEDIA_URL: str = "/media"
    DATABASE_URL_OVERRIDE: str | None = None

    @computed_field(return_type=str)
    @property
    def database_url(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return (
            f"postgresql+asyncpg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    @computed_field(return_type=Path)
    @property
    def media_path(self) -> Path:
        return Path(self.MEDIA_ROOT)

    @computed_field(return_type=str)
    @property
    def media_url_path(self) -> str:
        value = (self.MEDIA_URL or "/media").strip() or "/media"
        if not value.startswith("/"):
            value = f"/{value}"
        path = value.rstrip("/")
        return path or "/media"


settings = Settings()
