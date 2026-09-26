from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    FEATHERLESS_API_KEY: str = ""
    FEATHERLESS_BASE_URL: str = "https://api.featherless.ai/v1"
    FEATHERLESS_MODEL: str = "deepseek-ai/DeepSeek-V4.1-Flash"
    FEATHERLESS_TEXT_MODEL: str = "deepseek-ai/DeepSeek-V4.1-Flash"
    FEATHERLESS_TTS_MODEL: str = "hexgrad/Kokoro-82M"
    APP_ENV: str = "development"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = True


@lru_cache()
def get_settings() -> Settings:
    return Settings()
