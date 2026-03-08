from __future__ import annotations

from dataclasses import dataclass, field

from bacnet_lab.domain.enums import DeviceStatus, PointType
from bacnet_lab.domain.value_objects import DeviceAddress, PointValue


@dataclass
class Point:
    object_type: PointType
    object_instance: int
    object_name: str
    description: str = ""
    present_value: PointValue = 0.0
    units: str = ""
    cov_increment: float = 0.0

    @property
    def object_identifier(self) -> str:
        return f"{self.object_type},{self.object_instance}"


@dataclass
class Device:
    device_id: int
    name: str
    description: str = ""
    address: DeviceAddress | None = None
    status: DeviceStatus = DeviceStatus.ONLINE
    points: list[Point] = field(default_factory=list)

    def get_point(self, object_type: PointType, instance: int) -> Point | None:
        for p in self.points:
            if p.object_type == object_type and p.object_instance == instance:
                return p
        return None

    def get_point_by_name(self, name: str) -> Point | None:
        for p in self.points:
            if p.object_name == name:
                return p
        return None
