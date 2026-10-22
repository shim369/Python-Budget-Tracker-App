"""Application factory: API routers, static files and exception handlers.

Run with: uv run uvicorn app.main:app --reload   (single process; see DATA-01)
Design refs: MOD-01, MOD-20, ERR-03, ERR-30.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import Settings
from app.errors import register_exception_handlers
from app.repositories.json_store import JsonStore
from app.routers import budgets, categories, expenses, imports, status, subscriptions, summary


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app. Tests pass Settings pointing at a temporary data file."""
    settings = settings or Settings.from_env()
    store = JsonStore(settings.data_file)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        store.initialize()  # [ERR-30] recover from a corrupted file before serving
        yield

    app = FastAPI(
        title="Budget Tracker API",
        version="1.0.0",
        description="Expenses, subscriptions, budgets and CSV import. "
        "Errors use the unified format {error: {code, message, details}}.",
        lifespan=lifespan,
    )
    app.state.store = store
    register_exception_handlers(app)

    for module in (status, categories, expenses, subscriptions, budgets, summary, imports):
        app.include_router(module.router)

    index_file = settings.static_dir / "index.html"

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(index_file)

    app.mount("/static", StaticFiles(directory=settings.static_dir), name="static")
    _remove_default_422_from_openapi(app)
    return app


def _remove_default_422_from_openapi(app: FastAPI) -> None:
    """[ERR-03] Validation errors are returned as 400 in the unified format, never 422.

    FastAPI documents a 422 response on every endpoint with parameters; drop it so that
    /docs matches 03_api_design.md.
    """
    original = app.openapi

    def openapi() -> dict:
        if app.openapi_schema is not None:
            return app.openapi_schema
        schema = original()
        for operations in schema.get("paths", {}).values():
            for operation in operations.values():
                operation.get("responses", {}).pop("422", None)
        components = schema.get("components", {}).get("schemas", {})
        components.pop("HTTPValidationError", None)
        components.pop("ValidationError", None)
        app.openapi_schema = schema
        return schema

    app.openapi = openapi  # type: ignore[method-assign]


app = create_app()
