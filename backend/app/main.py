"""CodeMusume FastAPI application entry point."""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.endpoints import router
from app.routers.tts import router as tts_router

app = FastAPI(title="CodeMusume API", version="1.0.0")

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


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "app": "CodeMusume"}
