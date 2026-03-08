from bacnet_lab.domain.enums import (
    AlarmSeverity,
    DeviceStatus,
    EventType,
    PointType,
    ScenarioStatus,
)


def test_point_type_values():
    assert PointType.ANALOG_INPUT == "analogInput"
    assert PointType.BINARY_OUTPUT == "binaryOutput"


def test_device_status():
    assert DeviceStatus.ONLINE == "online"
    assert DeviceStatus.OFFLINE == "offline"


def test_scenario_status():
    assert ScenarioStatus.RUNNING == "running"


def test_event_type():
    assert EventType.POINT_VALUE_CHANGED == "point_value_changed"
    assert EventType.ALARM_RAISED == "alarm_raised"


def test_alarm_severity():
    assert AlarmSeverity.CRITICAL == "critical"
