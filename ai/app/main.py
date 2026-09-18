"""Application entrypoint for the Plane AI Gateway."""

import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import (
    chat,
    editor,
    execute,
    health,
    index,
    mcp,
    sessions,
    settings as settings_routes,
    skills,
    usage,
)
from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger, request_id_var
from app.db.session import dispose_engine, init_db

settings = get_settings()
configure_logging(settings.log_level)
logger = get_logger("gateway")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await dispose_engine()


app = FastAPI(
    title="Plane AI Gateway",
    version=__version__,
    description="Independent AI gateway for self-hosted Plane (Community Edition).",
    lifespan=lifespan,
)


@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex
    request_id_var.set(request_id)
    start = time.monotonic()
    response = await call_next(request)
    elapsed_ms = int((time.monotonic() - start) * 1000)
    response.headers["X-Request-Id"] = request_id
    logger.info("%s %s -> %s (%dms)", request.method, request.url.path, response.status_code, elapsed_ms)
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # same-origin via Caddy; tighten when exposing publicly
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(chat.router)
app.include_router(execute.router)
app.include_router(index.router)
app.include_router(editor.router)
app.include_router(skills.router)
app.include_router(mcp.router)
app.include_router(usage.router)
app.include_router(settings_routes.router)
app.include_router(sessions.router)
