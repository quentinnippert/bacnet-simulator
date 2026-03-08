from __future__ import annotations

from abc import ABC, abstractmethod

from bacnet_lab.domain.models.device import Device
from bacnet_lab.domain.models.endpoint import OutboundEndpoint
from bacnet_lab.domain.models.event import Alarm, ReplicationEvent


class DeviceRepositoryPort(ABC):
    @abstractmethod
    async def save(self, device: Device) -> None: ...

    @abstractmethod
    async def get(self, device_id: int) -> Device | None: ...

    @abstractmethod
    async def list_all(self) -> list[Device]: ...

    @abstractmethod
    async def update_point_value(
        self, device_id: int, point_name: str, value: float | int | bool | str
    ) -> None: ...

    @abstractmethod
    async def update_status(self, device_id: int, status: str) -> None: ...


class EndpointRepositoryPort(ABC):
    @abstractmethod
    async def save(self, endpoint: OutboundEndpoint) -> None: ...

    @abstractmethod
    async def get(self, endpoint_id: str) -> OutboundEndpoint | None: ...

    @abstractmethod
    async def list_all(self) -> list[OutboundEndpoint]: ...

    @abstractmethod
    async def delete(self, endpoint_id: str) -> None: ...

    @abstractmethod
    async def update_delivery_status(
        self, endpoint_id: str, success: bool
    ) -> None: ...


class EventLogRepositoryPort(ABC):
    @abstractmethod
    async def save(self, event: ReplicationEvent) -> None: ...

    @abstractmethod
    async def list_recent(self, limit: int = 50) -> list[ReplicationEvent]: ...

    @abstractmethod
    async def mark_delivered(self, event_id: str) -> None: ...


class AlarmRepositoryPort(ABC):
    @abstractmethod
    async def save(self, alarm: Alarm) -> None: ...

    @abstractmethod
    async def get_active(self) -> list[Alarm]: ...

    @abstractmethod
    async def clear(self, alarm_id: str) -> None: ...

    @abstractmethod
    async def list_recent(self, limit: int = 50) -> list[Alarm]: ...
