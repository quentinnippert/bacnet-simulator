"""Entry point: python -m bacnet_lab"""

from __future__ import annotations

import asyncio
import logging
import signal

import uvicorn

from bacnet_lab.adapters.http.app import create_app
from bacnet_lab.adapters.http.dependencies import set_container
from bacnet_lab.bootstrap import create_container
from bacnet_lab.infrastructure.config import load_settings
from bacnet_lab.infrastructure.logging import setup_logging

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_level)

    logger.info("Starting BACnet Lab...")
    container = await create_container(settings)
    set_container(container)

    await container.telemetry_service.start()

    app = create_app(
        auth_username=settings.auth.username,
        auth_password=settings.auth.password,
    )

    if settings.auth.enabled:
        logger.info("HTTP Basic Auth enabled (user: %s)", settings.auth.username)
    else:
        logger.warning("No auth configured — app is publicly accessible")

    config = uvicorn.Config(
        app,
        host=settings.http.host,
        port=settings.http.port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)

    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda: asyncio.create_task(shutdown(server, container)))

    logger.info("BACnet Lab ready on http://%s:%d", settings.http.host, settings.http.port)
    await server.serve()


async def shutdown(server: uvicorn.Server, container: object) -> None:
    logger.info("Shutting down...")
    server.should_exit = True
    await container.telemetry_service.stop()
    await container.device_service.shutdown()


if __name__ == "__main__":
    asyncio.run(main())
