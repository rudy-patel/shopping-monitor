"""FastAPI application entrypoint."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.logging import configure_logging
from core.settings import get_settings
from routers.health import router as health_router
from routers.profile import router as profile_router

settings = get_settings()
configure_logging(settings)

app = FastAPI(title="Shopping Monitor API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(profile_router)
