"""CodeMusume FastAPI application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router, scan_into_engine, start_lab_career
from app.core.config import get_settings
from app.routers.tts import router as tts_router
from app.routers.voice import router as voice_router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    # Agnes greets the trainer already knowing the trainee: the lab specimen
    # (a career, measured on startup) or the trainer's own repository.
    target = get_settings().TARGET_REPO_PATH
    if target.strip().lower() == "lab":
        await start_lab_career()
    else:
        scan_into_engine(target)
    yield


app = FastAPI(title="CodeMusume API", version="3.0.0", lifespan=lifespan)

# Allow all origins for local Vite / frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.include_router(tts_router)
app.include_router(voice_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": "CodeMusume"}
