from __future__ import annotations

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    model_validator,
)

from bacnet_lab.domain.enums import EventType, PointType

Value = StrictFloat | StrictInt | StrictBool | StrictStr


class Schema(BaseModel):
    model_config = ConfigDict(extra="forbid", from_attributes=True, allow_inf_nan=False)


class PointResponse(Schema):
    object_type: str
    object_instance: int
    object_name: str
    description: str
    present_value: Value
    units: str
    cov_increment: float
    state_text: list[str]
    commandable: bool


class DeviceResponse(Schema):
    device_id: int
    name: str
    description: str
    status: str
    point_count: int
    address: str | None
    error: str | None


class DeviceDetailResponse(Schema):
    device_id: int
    name: str
    description: str
    status: str
    points: list[PointResponse]
    address: dict | None
    error: str | None


class WritePointRequest(Schema):
    point_name: str | None = None
    object_type: PointType | None = None
    object_instance: int | None = Field(default=None, ge=0, le=4194302)
    value: Value | None
    priority: StrictInt = Field(default=16, ge=1, le=16)

    @model_validator(mode="after")
    def valid_target(self):
        by_name = self.point_name is not None
        by_id = self.object_type is not None and self.object_instance is not None
        if by_name == by_id or (
            by_name and (self.object_type is not None or self.object_instance is not None)
        ):
            raise ValueError("Specify either point_name or object_type + object_instance")
        if self.priority == 6:
            raise ValueError("Priority 6 is reserved")
        return self


class ScenarioResponse(Schema):
    id: str
    name: str
    description: str
    status: str
    parameters: list[dict]
    error: str | None


class StartScenarioRequest(Schema):
    params: dict | None = None


class EndpointCreateRequest(Schema):
    url: str = Field(min_length=1, max_length=2048)
    event_types: list[EventType] | None = None


class EndpointResponse(Schema):
    id: str
    url: str
    enabled: bool
    event_types: list[str]
    failure_count: int


class EndpointCreatedResponse(EndpointResponse):
    secret: str


class EventResponse(Schema):
    id: str
    event_type: str
    timestamp: str
    payload: dict
    delivered: bool


class AlarmResponse(Schema):
    id: str
    device_id: int
    point_name: str
    severity: str
    message: str
    raised_at: str
    cleared_at: str | None


class HealthResponse(Schema):
    status: str
    version: str
    devices_count: int
    online_devices: int
    active_scenarios: int
    errors: list[str]
