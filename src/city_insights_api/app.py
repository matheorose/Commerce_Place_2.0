"""Application factory for the FastAPI service."""

from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import router
from .core.config import settings

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    app = FastAPI(title="City Insights API", version="1.0.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    try:
        settings.ensure_files()
    except FileNotFoundError as exc:
        logger.warning("Configuration incomplète: %s", exc)

    app.include_router(router, prefix="/api")
    return app


app = create_app()
