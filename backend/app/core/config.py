from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    # Project-root .env first, backend/.env overrides it (whichever exists).
    model_config = SettingsConfigDict(
        env_file=(PROJECT_ROOT / ".env", BACKEND_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ASSEMBLYAI_API_KEY: str = ""
    ASSEMBLYAI_AGENTS_URL: str = "https://agents.assemblyai.com/v1"
    ASSEMBLYAI_VOICE: str = "vera"
    # "lab" starts a career on the bundled specimen; a path starts the free lab on that repo.
    TARGET_REPO_PATH: str = "lab"
    # Profile, trainee working copy and harness scratch space (gitignored).
    LAB_DATA_DIR: str = str(BACKEND_DIR / ".lab")

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
