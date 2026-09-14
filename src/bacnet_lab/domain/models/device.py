from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field

from bacnet_lab.domain.enums import DeviceStatus, PointType
from bacnet_lab.domain.errors import ValidationError
from bacnet_lab.domain.value_objects import DeviceAddress, PointValue


def _real(value, name: str) -> float:
    """Normalize a numeric property to the finite BACnet Real wire range."""
    if type(value) not in (int, float):
        raise ValidationError(f"{name} requires a finite number")
    try:
        normalized = struct.unpack("!f", struct.pack("!f", value))[0]
    except (OverflowError, struct.error) as exc:
        raise ValidationError(f"{name} exceeds BACnet Real range") from exc
    if not math.isfinite(normalized):
        raise ValidationError(f"{name} requires a finite number")
    return normalized


@dataclass
class Point:
    object_type: PointType
    object_instance: int
    object_name: str
    description: str = ""
    present_value: PointValue = 0.0
    units: str = ""
    cov_increment: float = 0.0
    state_text: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.object_type = PointType(self.object_type)
        if type(self.object_instance) is not int or not 0 <= self.object_instance <= 4194302:
            raise ValidationError("Object instance must be between 0 and 4194302")
        if (
            not isinstance(self.object_name, str)
            or not self.object_name
            or len(self.object_name) > 255
        ):
            raise ValidationError("Point name must contain 1–255 characters")
        self.cov_increment = _real(self.cov_increment, "COV increment")
        if self.cov_increment < 0:
            raise ValidationError("COV increment must be non-negative")
        if not isinstance(self.state_text, list):
            raise ValidationError("state_text must be a list of labels")
        if self.state_text and not self.object_type.value.startswith("multiState"):
            raise ValidationError("state_text is only valid for multistate points")
        if self.object_type.value.startswith("multiState"):
            if not self.state_text or any(not isinstance(s, str) or not s for s in self.state_text):
                raise ValidationError("Multistate points require non-empty state_text labels")
        self.present_value = self.validate_value(self.present_value)

    @property
    def commandable(self) -> bool:
        return not self.object_type.value.endswith("Input")

    def validate_value(self, value: PointValue) -> PointValue:
        kind = self.object_type.value
        if kind.startswith("binary"):
            if type(value) is not bool:
                raise ValidationError(f"{self.object_name} requires a boolean")
            return value
        if kind.startswith("multiState"):
            if type(value) is not int or not 1 <= value <= len(self.state_text):
                raise ValidationError(
                    f"{self.object_name} requires an integer in 1..{len(self.state_text)}"
                )
            return value
        normalized = _real(value, self.object_name)
        if self.units in ("percent", "percentRelativeHumidity") and not 0 <= value <= 100:
            raise ValidationError(f"{self.object_name} requires a value in 0..100")
        return normalized

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
    error: str | None = None

    def __post_init__(self) -> None:
        if type(self.device_id) is not int or not 0 <= self.device_id <= 4194302:
            raise ValidationError("Device ID must be between 0 and 4194302")
        if not self.name or len(self.name) > 255:
            raise ValidationError("Device name must contain 1–255 characters")
        names = [p.object_name for p in self.points]
        identifiers = [p.object_identifier for p in self.points]
        if len(set(names)) != len(names) or len(set(identifiers)) != len(identifiers):
            raise ValidationError(f"Duplicate point name or identifier on {self.name}")

    def get_point(self, object_type: PointType, instance: int) -> Point | None:
        return next(
            (
                p
                for p in self.points
                if p.object_type == object_type and p.object_instance == instance
            ),
            None,
        )

    def get_point_by_name(self, name: str) -> Point | None:
        return next((p for p in self.points if p.object_name == name), None)
