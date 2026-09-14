"""Run one ASGI worker; the lifespan owns all simulation resources."""

import uvicorn

from bacnet_lab.adapters.http.app import create_app
from bacnet_lab.infrastructure.config import load_settings
from bacnet_lab.infrastructure.logging import setup_logging


def main() -> None:
    settings = load_settings()
    setup_logging(settings.log_level)
    uvicorn.run(
        create_app(settings=settings),
        host=settings.http.host,
        port=settings.http.port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    main()
