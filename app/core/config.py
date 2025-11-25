from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="MOSIC_"
    )
    APP_NAME: str = "Mosic"

    DB_HOST: str = "db"
    DB_PORT: int = 5432
    DB_NAME: str = "mosic"
    DB_USER: str = "mosic"
    DB_PASSWORD: str = "mosicpassword"
    ECHO_SQL: bool = False
    DATABASE_URL_OVERRIDE: str | None = None

    @computed_field(return_type=str)
    @property
    def database_url(self) -> str:
        if self.DATABASE_URL_OVERRIDE:
            return self.DATABASE_URL_OVERRIDE
        return (
            f"postgresql+psycopg://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )


settings = Settings()
