from enum import StrEnum


class PointType(StrEnum):
    ANALOG_INPUT = "analogInput"
    ANALOG_OUTPUT = "analogOutput"
    ANALOG_VALUE = "analogValue"
    BINARY_INPUT = "binaryInput"
    BINARY_OUTPUT = "binaryOutput"
    BINARY_VALUE = "binaryValue"
    MULTI_STATE_INPUT = "multiStateInput"
    MULTI_STATE_OUTPUT = "multiStateOutput"
    MULTI_STATE_VALUE = "multiStateValue"


class DeviceStatus(StrEnum):
    ONLINE = "online"
    OFFLINE = "offline"
    ERROR = "error"


class ScenarioStatus(StrEnum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


class EventType(StrEnum):
    POINT_VALUE_CHANGED = "point_value_changed"
    DEVICE_STATUS_CHANGED = "device_status_changed"
    ALARM_RAISED = "alarm_raised"
    ALARM_CLEARED = "alarm_cleared"
    SCENARIO_STARTED = "scenario_started"
    SCENARIO_STOPPED = "scenario_stopped"
    TELEMETRY_SNAPSHOT = "telemetry_snapshot"


class AlarmSeverity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
