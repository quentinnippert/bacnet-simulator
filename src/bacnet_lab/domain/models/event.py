from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from bacnet_lab.domain.enums import AlarmSeverity, EventType


@dataclass
class ReplicationEvent:
    id: str
    event_type: EventType
    timestamp: datetime
    payload: dict
    delivered: bool = False


@dataclass
class Alarm:
    id: str
    device_id: int
    point_name: str
    severity: AlarmSeverity
    message: str
    raised_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    cleared_at: datetime | None = None

    @property
    def is_active(self) -> bool:
        return self.cleared_at is None


@dataclass
class TelemetrySnapshot:
    timestamp: datetime
    device_id: int
    points: dict[str, float | int | bool | str]
