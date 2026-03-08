import asyncio
import os
import tempfile

import pytest
from httpx import ASGITransport, AsyncClient

from bacnet_lab.adapters.bacnet.device_factory import load_all_devices
from bacnet_lab.adapters.event_bus.in_process import InProcessEventPublisher
from bacnet_lab.adapters.http.app import create_app
from bacnet_lab.adapters.http.dependencies import set_container
from bacnet_lab.adapters.persistence.migrations import run_migrations
from bacnet_lab.adapters.persistence.sqlite_repos import (
    SqliteAlarmRepository,
    SqliteDeviceRepository,
    SqliteEndpointRepository,
    SqliteEventLogRepository,
)
from bacnet_lab.adapters.scenarios.registry import ScenarioRegistry
from bacnet_lab.adapters.webhook.delivery import WebhookDeliveryAdapter
from bacnet_lab.application.device_service import DeviceService
from bacnet_lab.application.endpoint_service import EndpointService
from bacnet_lab.application.event_service import EventService
from bacnet_lab.application.scenario_service import ScenarioService
from bacnet_lab.application.telemetry_service import TelemetryService
from bacnet_lab.bootstrap import Container
from bacnet_lab.domain.enums import PointType
from bacnet_lab.domain.models.device import Device, Point
from bacnet_lab.domain.value_objects import PointValue
from bacnet_lab.infrastructure.config import AppSettings
from bacnet_lab.ports.device_network import DeviceNetworkPort


class FakeNetwork(DeviceNetworkPort):
    """In-memory fake for tests (no BAC0 needed)."""

    def __init__(self):
        self._devices: dict[int, Device] = {}

    async def start_device(self, device: Device, udp_port: int) -> None:
        self._devices[device.device_id] = device

    async def stop_device(self, device_id: int) -> None:
        self._devices.pop(device_id, None)

    async def stop_all(self) -> None:
        self._devices.clear()

    async def write_point_value(
        self, device_id: int, object_type: PointType, instance: int, value: PointValue
    ) -> None:
        device = self._devices.get(device_id)
        if device:
            point = device.get_point(object_type, instance)
            if point:
                point.present_value = value

    async def read_point_value(
        self, device_id: int, object_type: PointType, instance: int
    ) -> PointValue:
        device = self._devices.get(device_id)
        if device:
            point = device.get_point(object_type, instance)
            if point:
                return point.present_value
        return 0


@pytest.fixture
async def client():
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    await run_migrations(db_path)

    settings = AppSettings(db_path=db_path)
    event_publisher = InProcessEventPublisher()
    network = FakeNetwork()
    device_repo = SqliteDeviceRepository(db_path)
    endpoint_repo = SqliteEndpointRepository(db_path)
    event_log_repo = SqliteEventLogRepository(db_path)
    alarm_repo = SqliteAlarmRepository(db_path)
    webhook_delivery = WebhookDeliveryAdapter()

    device_service = DeviceService(
        device_repo=device_repo, network=network, event_publisher=event_publisher
    )
    scenario_registry = ScenarioRegistry()
    scenario_service = ScenarioService(runner=scenario_registry)
    endpoint_service = EndpointService(repo=endpoint_repo, delivery=webhook_delivery)
    event_service = EventService(
        event_publisher=event_publisher,
        event_log_repo=event_log_repo,
        endpoint_repo=endpoint_repo,
        delivery=webhook_delivery,
    )
    telemetry_service = TelemetryService(event_publisher=event_publisher)

    # Load test devices
    devices = load_all_devices("config/devices")
    await device_service.initialize_devices(devices)

    container = Container(
        settings=settings,
        device_service=device_service,
        scenario_service=scenario_service,
        endpoint_service=endpoint_service,
        event_service=event_service,
        telemetry_service=telemetry_service,
        alarm_repo=alarm_repo,
        engine=None,
        event_publisher=event_publisher,
    )
    set_container(container)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    os.unlink(db_path)


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["devices_count"] == 7


@pytest.mark.asyncio
async def test_list_devices(client):
    resp = await client.get("/api/devices")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 7


@pytest.mark.asyncio
async def test_get_device(client):
    resp = await client.get("/api/devices/1001")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "AHU-01"
    assert len(data["points"]) == 12


@pytest.mark.asyncio
async def test_get_device_not_found(client):
    resp = await client.get("/api/devices/9999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_write_point(client):
    resp = await client.put(
        "/api/devices/1001/points",
        json={"point_name": "AHU-01/CoolingValve", "value": 80.0},
    )
    assert resp.status_code == 200

    resp = await client.get("/api/devices/1001")
    data = resp.json()
    cooling = next(p for p in data["points"] if p["object_name"] == "AHU-01/CoolingValve")
    assert cooling["present_value"] == 80.0


@pytest.mark.asyncio
async def test_list_scenarios(client):
    resp = await client.get("/api/scenarios")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_events(client):
    resp = await client.get("/api/events")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_list_alarms(client):
    resp = await client.get("/api/alarms")
    assert resp.status_code == 200
