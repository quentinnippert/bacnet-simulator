from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from bacnet_lab.domain.enums import AlarmSeverity, DeviceStatus, EventType, ScenarioStatus
from bacnet_lab.domain.value_objects import PointValue


@dataclass
class DomainEvent:
    event_type: EventType
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class PointValueChanged(DomainEvent):
    device_id: int = 0
    point_name: str = ""
    old_value: PointValue = 0.0
    new_value: PointValue = 0.0
    event_type: EventType = field(default=EventType.POINT_VALUE_CHANGED, init=False)


@dataclass
class DeviceStatusChanged(DomainEvent):
    device_id: int = 0
    old_status: DeviceStatus = DeviceStatus.ONLINE
    new_status: DeviceStatus = DeviceStatus.ONLINE
    event_type: EventType = field(default=EventType.DEVICE_STATUS_CHANGED, init=False)


@dataclass
class AlarmRaised(DomainEvent):
    alarm_id: str = ""
    device_id: int = 0
    point_name: str = ""
    severity: AlarmSeverity = AlarmSeverity.MEDIUM
    message: str = ""
    event_type: EventType = field(default=EventType.ALARM_RAISED, init=False)


@dataclass
class AlarmCleared(DomainEvent):
    alarm_id: str = ""
    device_id: int = 0
    point_name: str = ""
    event_type: EventType = field(default=EventType.ALARM_CLEARED, init=False)


@dataclass
class ScenarioLifecycleChanged(DomainEvent):
    scenario_id: str = ""
    new_status: ScenarioStatus = ScenarioStatus.IDLE
    event_type: EventType = field(default=EventType.SCENARIO_STARTED, init=False)

    def __post_init__(self) -> None:
        if self.new_status == ScenarioStatus.RUNNING:
            self.event_type = EventType.SCENARIO_STARTED
        elif self.new_status in (ScenarioStatus.STOPPED, ScenarioStatus.IDLE):
            self.event_type = EventType.SCENARIO_STOPPED
