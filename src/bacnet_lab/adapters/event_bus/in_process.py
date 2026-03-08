from __future__ import annotations

import logging

from bacnet_lab.domain.events import DomainEvent
from bacnet_lab.ports.event_publisher import EventHandler, EventPublisherPort

logger = logging.getLogger(__name__)


class InProcessEventPublisher(EventPublisherPort):
    def __init__(self) -> None:
        self._handlers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler) -> None:
        self._handlers.append(handler)

    async def publish(self, event: DomainEvent) -> None:
        for handler in self._handlers:
            try:
                await handler(event)
            except Exception as e:
                logger.error("Event handler error for %s: %s", event.event_type, e)
