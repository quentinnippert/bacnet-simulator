import asyncio
import os
import tempfile

import pytest

from bacnet_lab.adapters.persistence.migrations import run_migrations
from bacnet_lab.adapters.persistence.sqlite_repos import (
    SqliteAlarmRepository,
    SqliteDeviceRepository,
    SqliteEndpointRepository,
    SqliteEventLogRepository,
)
from bacnet_lab.domain.enums import (
    AlarmSeverity,
    DeviceStatus,
    EventType,
    PointType,
)
from bacnet_lab.domain.models.device import Device, Point
from bacnet_lab.domain.models.endpoint import OutboundEndpoint
from bacnet_lab.domain.models.event import Alarm, ReplicationEvent
from bacnet_lab.domain.value_objects import DeviceAddress
from datetime import datetime, timezone


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    asyncio.get_event_loop().run_until_complete(run_migrations(path))
    yield path
    os.unlink(path)


@pytest.fixture
def device_repo(db_path):
    return SqliteDeviceRepository(db_path)


@pytest.fixture
def endpoint_repo(db_path):
    return SqliteEndpointRepository(db_path)


@pytest.fixture
def event_repo(db_path):
    return SqliteEventLogRepository(db_path)


@pytest.fixture
def alarm_repo(db_path):
    return SqliteAlarmRepository(db_path)


@pytest.mark.asyncio
async def test_device_save_and_get(device_repo):
    device = Device(
        device_id=1001,
        name="AHU-01",
        description="Test",
        address=DeviceAddress(ip="127.0.0.1", port=47808),
        status=DeviceStatus.ONLINE,
        points=[
            Point(
                object_type=PointType.ANALOG_INPUT,
                object_instance=1,
                object_name="AHU-01/Temp",
                present_value=22.5,
                units="degreesCelsius",
            )
        ],
    )
    await device_repo.save(device)

    loaded = await device_repo.get(1001)
    assert loaded is not None
    assert loaded.name == "AHU-01"
    assert len(loaded.points) == 1
    assert loaded.points[0].present_value == 22.5


@pytest.mark.asyncio
async def test_device_list_all(device_repo):
    for did in [1001, 2001, 3001]:
        await device_repo.save(Device(device_id=did, name=f"DEV-{did}"))
    devices = await device_repo.list_all()
    assert len(devices) == 3


@pytest.mark.asyncio
async def test_device_update_point_value(device_repo):
    device = Device(
        device_id=1001,
        name="AHU-01",
        points=[
            Point(
                object_type=PointType.ANALOG_INPUT,
                object_instance=1,
                object_name="AHU-01/Temp",
                present_value=22.5,
            )
        ],
    )
    await device_repo.save(device)
    await device_repo.update_point_value(1001, "AHU-01/Temp", 25.0)

    loaded = await device_repo.get(1001)
    assert loaded.points[0].present_value == 25.0


@pytest.mark.asyncio
async def test_endpoint_crud(endpoint_repo):
    ep = OutboundEndpoint(
        id="ep1",
        url="https://example.com/hook",
        secret="secret123",
        enabled=True,
        event_types=[EventType.POINT_VALUE_CHANGED],
        created_at=datetime.now(timezone.utc),
    )
    await endpoint_repo.save(ep)

    loaded = await endpoint_repo.get("ep1")
    assert loaded is not None
    assert loaded.url == "https://example.com/hook"

    all_eps = await endpoint_repo.list_all()
    assert len(all_eps) == 1

    await endpoint_repo.delete("ep1")
    assert await endpoint_repo.get("ep1") is None


@pytest.mark.asyncio
async def test_event_log(event_repo):
    event = ReplicationEvent(
        id="evt1",
        event_type=EventType.POINT_VALUE_CHANGED,
        timestamp=datetime.now(timezone.utc),
        payload={"test": True},
    )
    await event_repo.save(event)

    events = await event_repo.list_recent()
    assert len(events) == 1
    assert events[0].id == "evt1"

    await event_repo.mark_delivered("evt1")
    events = await event_repo.list_recent()
    assert events[0].delivered is True


@pytest.mark.asyncio
async def test_alarm_repo(alarm_repo):
    alarm = Alarm(
        id="alm1",
        device_id=1001,
        point_name="AHU-01/Temp",
        severity=AlarmSeverity.HIGH,
        message="Too hot",
        raised_at=datetime.now(timezone.utc),
    )
    await alarm_repo.save(alarm)

    active = await alarm_repo.get_active()
    assert len(active) == 1

    await alarm_repo.clear("alm1")
    active = await alarm_repo.get_active()
    assert len(active) == 0

    recent = await alarm_repo.list_recent()
    assert len(recent) == 1
    assert recent[0].cleared_at is not None
