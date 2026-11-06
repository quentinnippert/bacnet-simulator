from __future__ import annotations

from abc import ABC, abstractmethod

from bacnet_lab.domain.enums import PointType
from bacnet_lab.domain.models.device import Device, PointStatus
from bacnet_lab.domain.value_objects import PointValue


class DeviceNetworkPort(ABC):
    async def read_point_status(
        self, device_id: int, object_type: PointType, instance: int
    ) -> PointStatus:
        raise NotImplementedError("Point status is not implemented by this adapter")

    async def set_point_status(
        self,
        device_id: int,
        object_type: PointType,
        instance: int,
        *,
        out_of_service: bool | None = None,
        reliability: str | None = None,
    ) -> None:
        raise NotImplementedError("Simulator status control is not implemented by this adapter")

    @abstractmethod
    async def start_device(self, device: Device, udp_port: int) -> None: ...

    @abstractmethod
    async def stop_device(self, device_id: int) -> None: ...

    @abstractmethod
    async def stop_all(self) -> None: ...

    @abstractmethod
    async def write_point_value(
        self,
        device_id: int,
        object_type: PointType,
        instance: int,
        value: PointValue | None,
        priority: int = 16,
    ) -> int:
        """Write a command/sensor source and return its revision, including same-value writes."""
        ...

    @abstractmethod
    async def read_point_value(
        self, device_id: int, object_type: PointType, instance: int
    ) -> PointValue: ...

    @abstractmethod
    async def read_priority_value(
        self, device_id: int, object_type: PointType, instance: int, priority: int
    ) -> PointValue | None: ...

    @abstractmethod
    async def read_control_state(
        self, device_id: int, object_type: PointType, instance: int, priority: int
    ) -> tuple[PointValue | None, int]:
        """Return the priority slot (or simulated physical input) and its write revision."""
        ...
