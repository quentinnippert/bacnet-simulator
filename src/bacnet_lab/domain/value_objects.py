from __future__ import annotations

from dataclasses import dataclass

PointValue = float | int | bool | str


@dataclass(frozen=True)
class DeviceAddress:
    ip: str
    port: int

    def __str__(self) -> str:
        return f"{self.ip}:{self.port}"
