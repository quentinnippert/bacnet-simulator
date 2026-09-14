from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Coroutine

from bacnet_lab.domain.events import DomainEvent

EventHandler = Callable[[DomainEvent], Coroutine]


class EventPublisherPort(ABC):
    @abstractmethod
    def subscribe(self, handler: EventHandler) -> None: ...

    @abstractmethod
    async def publish(self, event: DomainEvent) -> None: ...
