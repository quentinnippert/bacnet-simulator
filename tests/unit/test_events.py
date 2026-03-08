from bacnet_lab.domain.enums import AlarmSeverity, DeviceStatus, EventType, ScenarioStatus
from bacnet_lab.domain.events import (
    AlarmCleared,
    AlarmRaised,
    DeviceStatusChanged,
    PointValueChanged,
    ScenarioLifecycleChanged,
)


def test_point_value_changed():
    event = PointValueChanged(device_id=1001, point_name="test", old_value=1.0, new_value=2.0)
    assert event.event_type == EventType.POINT_VALUE_CHANGED
    assert event.device_id == 1001


def test_device_status_changed():
    event = DeviceStatusChanged(
        device_id=1001, old_status=DeviceStatus.ONLINE, new_status=DeviceStatus.OFFLINE
    )
    assert event.event_type == EventType.DEVICE_STATUS_CHANGED


def test_alarm_raised():
    event = AlarmRaised(
        alarm_id="abc", device_id=1001, point_name="test",
        severity=AlarmSeverity.HIGH, message="too hot",
    )
    assert event.event_type == EventType.ALARM_RAISED


def test_alarm_cleared():
    event = AlarmCleared(alarm_id="abc", device_id=1001, point_name="test")
    assert event.event_type == EventType.ALARM_CLEARED


def test_scenario_lifecycle_running():
    event = ScenarioLifecycleChanged(scenario_id="test", new_status=ScenarioStatus.RUNNING)
    assert event.event_type == EventType.SCENARIO_STARTED


def test_scenario_lifecycle_stopped():
    event = ScenarioLifecycleChanged(scenario_id="test", new_status=ScenarioStatus.STOPPED)
    assert event.event_type == EventType.SCENARIO_STOPPED
