"""FastAPI application entry point for the Nexus-Intel backend.

Run from the repository root::

    uvicorn app.main:app --reload --port 8000

Swagger UI: http://localhost:8000/docs (ReDoc at /redoc, OpenAPI at
/openapi.json). CORS origins, MongoDB settings and the pipeline timeout are
read from environment variables (see ``app/config.py`` and ``.env.example``).
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import AsyncIterator, Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pymongo.errors import PyMongoError

from app import config, database
from app.errors import register_exception_handlers
from app.routers import analyze, competitors
from app.schemas import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("nexus_intel.api")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Connect MongoDB on startup, close it on shutdown.

    A down database must not prevent the API from booting: the health endpoint
    reports ``"database": "unavailable"`` and persistence endpoints return a
    503 envelope instead of crashing.
    """
    try:
        await database.connect_db()
    except PyMongoError:
        logger.warning(
            "MongoDB is not reachable at startup; "
            "the API will start but persistence endpoints will return 503."
        )
    yield
    await database.close_db()


app = FastAPI(
    title=config.API_TITLE,
    version=config.API_VERSION,
    description=config.API_DESCRIPTION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=config.CORS_ALLOW_CREDENTIALS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(analyze.router, prefix="/api/v1")
app.include_router(competitors.router, prefix="/api/v1")


@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
)
async def health(request: Request) -> HealthResponse:
    """Liveness/health probe: never exposes connection strings or credentials."""
    db_ok = database.is_connected()
    if db_ok:
        # Cheap re-check: a previously healthy connection may have dropped.
        try:
            await database.get_database().command("ping")
        except PyMongoError:
            db_ok = False

    return HealthResponse(
        status="ok" if db_ok else "degraded",
        version=config.API_VERSION,
        mock_mode=config.MOCK_MODE,
        database="connected" if db_ok else "unavailable",
        timestamp=datetime.now(timezone.utc),
    )


@app.get("/", include_in_schema=False)
async def root() -> dict:
    """Convenience pointer to the interactive documentation."""
    return {
        "service": "nexus-intel-api",
        "version": config.API_VERSION,
        "docs": "/docs",
        "health": "/health",
    }
