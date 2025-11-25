from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="MOSIC_"
    )
    APP_NAME: str = "Mosic"


settings = Settings()
