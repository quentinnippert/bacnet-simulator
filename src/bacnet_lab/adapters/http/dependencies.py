from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bacnet_lab.bootstrap import Container

_container: Container | None = None


def set_container(container: Container) -> None:
    global _container
    _container = container


def get_container() -> Container:
    if _container is None:
        raise RuntimeError("Container not initialized")
    return _container
