from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from bacnet_lab.adapters.http.routers import devices, endpoints, events, health, scenarios


def create_app(auth_username: str = "", auth_password: str = "") -> FastAPI:
    app = FastAPI(title="BACnet Lab", version="0.1.0")

    if auth_username and auth_password:
        from bacnet_lab.adapters.http.auth import BasicAuthMiddleware

        app.add_middleware(BasicAuthMiddleware, username=auth_username, password=auth_password)

    app.include_router(health.router)
    app.include_router(devices.router)
    app.include_router(scenarios.router)
    app.include_router(endpoints.router)
    app.include_router(events.router)

    # Web UI
    from bacnet_lab.adapters.web.router import router as web_router

    app.include_router(web_router)

    static_dir = Path(__file__).parent.parent / "web" / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app
