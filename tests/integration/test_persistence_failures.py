import sqlite3
import time
from datetime import UTC, datetime

import pytest

from bacnet_lab.adapters.persistence.migrations import TABLES, run_migrations
from bacnet_lab.adapters.persistence.sqlite_repos import (
    SqliteAlarmRepository,
    SqliteEndpointRepository,
    SqliteEventLogRepository,
)
from bacnet_lab.domain.enums import EventType
from bacnet_lab.domain.models.endpoint import OutboundEndpoint
from bacnet_lab.domain.models.event import ReplicationEvent


@pytest.mark.asyncio
async def test_legacy_migration_preserves_values_endpoints_and_is_idempotent(tmp_path):
    path = str(tmp_path / "legacy.db")
    with sqlite3.connect(path) as db:
        for sql in TABLES:
            db.execute(sql)
        db.execute("INSERT INTO devices (device_id,name) VALUES (1001,'AHU')")
        db.execute(
            "INSERT INTO points (device_id,object_type,object_instance,object_name,present_value) VALUES (1001,'analogInput',1,'Temperature','1e-07')"
        )
        db.execute(
            "INSERT INTO endpoints (id,url,secret) VALUES ('ep','http://localhost/hook','existing-secret')"
        )
    await run_migrations(path)
    await run_migrations(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 2
        assert db.execute("SELECT present_value FROM points").fetchone()[0] == "1e-07"
        assert db.execute("SELECT secret FROM endpoints").fetchone()[0] == "existing-secret"
        assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"


@pytest.mark.asyncio
async def test_unknown_future_schema_is_not_modified(tmp_path):
    path = str(tmp_path / "future.db")
    with sqlite3.connect(path) as db:
        db.execute("PRAGMA user_version=999")
    with pytest.raises(RuntimeError, match="Unsupported database"):
        await run_migrations(path)
    with sqlite3.connect(path) as db:
        assert db.execute("PRAGMA user_version").fetchone()[0] == 999


@pytest.mark.asyncio
async def test_event_targets_and_alarm_projection_are_atomic(tmp_path):
    path = str(tmp_path / "db")
    await run_migrations(path)
    event = ReplicationEvent(
        "event",
        EventType.ALARM_RAISED,
        datetime.now(UTC),
        {
            "alarm_id": "alarm",
            "device_id": 1001,
            "point_name": "Temperature",
            "severity": "high",
            "message": "test",
        },
    )
    repo = SqliteEventLogRepository(path)
    with pytest.raises(sqlite3.IntegrityError):
        await repo.record(event, ["missing-endpoint"])
    assert not await repo.list_recent()
    assert not await SqliteAlarmRepository(path).get_active()
    await repo.record(event, [])
    assert len(await repo.list_recent()) == 1
    assert len(await SqliteAlarmRepository(path).get_active()) == 1


@pytest.mark.asyncio
async def test_endpoint_deletion_cancels_pending_delivery_safely(tmp_path):
    path = str(tmp_path / "db")
    await run_migrations(path)
    endpoints = SqliteEndpointRepository(path)
    repo = SqliteEventLogRepository(path)
    await endpoints.save(OutboundEndpoint("ep", "http://localhost/hook", "secret"))
    await repo.record(
        ReplicationEvent("event", EventType.TELEMETRY_SNAPSHOT, datetime.now(UTC), {}), ["ep"]
    )
    delivery = (await repo.pending_deliveries(time.time()))[0]
    await endpoints.delete("ep")
    await repo.finish_delivery(delivery["id"], True, time.time())
    assert not await repo.delivery_history()
