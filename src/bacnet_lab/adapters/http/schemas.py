from __future__ import annotations

from pydantic import BaseModel

from bacnet_lab.domain.enums import EventType


class PointResponse(BaseModel):
    object_type: str
    object_instance: int
    object_name: str
    description: str
    present_value: float | int | bool | str
    units: str


class DeviceResponse(BaseModel):
    device_id: int
    name: str
    description: str
    status: str
    point_count: int


class DeviceDetailResponse(BaseModel):
    device_id: int
    name: str
    description: str
    status: str
    points: list[PointResponse]


class WritePointRequest(BaseModel):
    object_type: str
    object_instance: int
    value: float | int | bool | str


class WritePointByNameRequest(BaseModel):
    point_name: str
    value: float | int | bool | str


class ScenarioResponse(BaseModel):
    id: str
    name: str
    description: str
    status: str


class StartScenarioRequest(BaseModel):
    params: dict | None = None


class EndpointCreateRequest(BaseModel):
    url: str
    event_types: list[EventType] | None = None


class EndpointResponse(BaseModel):
    id: str
    url: str
    secret: str
    enabled: bool
    event_types: list[str]
    failure_count: int


class EventResponse(BaseModel):
    id: str
    event_type: str
    timestamp: str
    payload: dict
    delivered: bool


class AlarmResponse(BaseModel):
    id: str
    device_id: int
    point_name: str
    severity: str
    message: str
    raised_at: str
    cleared_at: str | None


class HealthResponse(BaseModel):
    status: str
    version: str
    devices_count: int
    active_scenarios: int
