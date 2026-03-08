from __future__ import annotations

from abc import ABC, abstractmethod

from bacnet_lab.domain.models.endpoint import OutboundEndpoint
from bacnet_lab.domain.models.event import ReplicationEvent


class EventDeliveryPort(ABC):
    @abstractmethod
    async def deliver(self, event: ReplicationEvent, endpoint: OutboundEndpoint) -> bool: ...
