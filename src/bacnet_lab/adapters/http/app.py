from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from bacnet_lab.adapters.http.routers import devices, endpoints, events, health, scenarios
from bacnet_lab.bootstrap import Container, create_container
from bacnet_lab.domain.errors import ConflictError, NotFoundError, UnavailableError, ValidationError
from bacnet_lab.infrastructure.config import AppSettings, AuthSettings, load_settings

logger = logging.getLogger(__name__)


def create_app(
    auth_username: str = "",
    auth_password: str = "",
    *,
    container: Container | None = None,
    settings: AppSettings | None = None,
) -> FastAPI:
    settings = settings or (container.settings if container else load_settings())
    auth = (
        AuthSettings(username=auth_username, password=auth_password)
        if auth_username or auth_password
        else settings.auth
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        resources = container or await create_container(settings)
        app.state.container = resources
        try:
            await resources.start()
            yield
        finally:
            await resources.close()

    app = FastAPI(title="BACnet Lab", version="0.1.0", lifespan=lifespan)
    if container is not None:
        app.state.container = container
    if auth.enabled:
        from bacnet_lab.adapters.http.auth import BasicAuthMiddleware

        app.add_middleware(BasicAuthMiddleware, username=auth.username, password=auth.password)

    @app.exception_handler(ValidationError)
    @app.exception_handler(NotFoundError)
    @app.exception_handler(ConflictError)
    @app.exception_handler(UnavailableError)
    async def application_error(request: Request, exc: Exception):
        status = {
            ValidationError: 422,
            NotFoundError: 404,
            ConflictError: 409,
            UnavailableError: 503,
        }[type(exc)]
        return JSONResponse(status_code=status, content={"detail": str(exc)})

    @app.middleware("http")
    async def same_origin_commands(request: Request, call_next):
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            expected = f"{request.url.scheme}://{request.url.netloc}"
            if (origin and origin != expected) or request.headers.get(
                "sec-fetch-site"
            ) == "cross-site":
                return JSONResponse(
                    status_code=403, content={"detail": "Cross-origin commands are not allowed"}
                )
        return await call_next(request)

    for router in (
        health.router,
        devices.router,
        scenarios.router,
        endpoints.router,
        events.router,
    ):
        app.include_router(router)
    from bacnet_lab.adapters.web.router import router as web_router

    app.include_router(web_router)
    app.mount(
        "/static",
        StaticFiles(directory=str(Path(__file__).parent.parent / "web" / "static")),
        name="static",
    )
    return app
