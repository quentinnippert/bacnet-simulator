from __future__ import annotations

from abc import ABC, abstractmethod

from bacnet_lab.domain.enums import PointType
from bacnet_lab.domain.models.device import Device
from bacnet_lab.domain.value_objects import PointValue


class DeviceNetworkPort(ABC):
    @abstractmethod
    async def start_device(self, device: Device, udp_port: int) -> None: ...

    @abstractmethod
    async def stop_device(self, device_id: int) -> None: ...

    @abstractmethod
    async def stop_all(self) -> None: ...

    @abstractmethod
    async def write_point_value(
        self, device_id: int, object_type: PointType, instance: int, value: PointValue
    ) -> None: ...

    @abstractmethod
    async def read_point_value(
        self, device_id: int, object_type: PointType, instance: int
    ) -> PointValue: ...
