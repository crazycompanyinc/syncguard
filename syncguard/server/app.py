"""FastAPI app factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from syncguard.server.routes import build_router


def create_app(root: str | Path = ".") -> FastAPI:
    app = FastAPI(title="SyncGuard", version="2.0.0")
    app.include_router(build_router(root))
    return app


app = create_app()
