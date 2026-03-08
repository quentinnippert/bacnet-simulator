from __future__ import annotations

import json
from datetime import datetime, timezone

import aiosqlite

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
from bacnet_lab.ports.repositories import (
    AlarmRepositoryPort,
    DeviceRepositoryPort,
    EndpointRepositoryPort,
    EventLogRepositoryPort,
)


def _parse_value(raw: str) -> float | int | bool | str:
    if raw in ("true", "True"):
        return True
    if raw in ("false", "False"):
        return False
    try:
        if "." in raw:
            return float(raw)
        return int(raw)
    except (ValueError, TypeError):
        return raw


class SqliteDeviceRepository(DeviceRepositoryPort):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def save(self, device: Device) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO devices (device_id, name, description, ip, port, status) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    device.device_id,
                    device.name,
                    device.description,
                    device.address.ip if device.address else "",
                    device.address.port if device.address else 0,
                    device.status.value,
                ),
            )
            for point in device.points:
                await db.execute(
                    "INSERT OR REPLACE INTO points "
                    "(device_id, object_type, object_instance, object_name, "
                    "description, present_value, units, cov_increment) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        device.device_id,
                        point.object_type.value,
                        point.object_instance,
                        point.object_name,
                        point.description,
                        str(point.present_value),
                        point.units,
                        point.cov_increment,
                    ),
                )
            await db.commit()

    async def get(self, device_id: int) -> Device | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM devices WHERE device_id = ?", (device_id,)
            )
            row = await cursor.fetchone()
            if not row:
                return None
            cursor = await db.execute(
                "SELECT * FROM points WHERE device_id = ?", (device_id,)
            )
            point_rows = await cursor.fetchall()
            points = [
                Point(
                    object_type=PointType(pr["object_type"]),
                    object_instance=pr["object_instance"],
                    object_name=pr["object_name"],
                    description=pr["description"],
                    present_value=_parse_value(pr["present_value"]),
                    units=pr["units"],
                    cov_increment=pr["cov_increment"],
                )
                for pr in point_rows
            ]
            return Device(
                device_id=row["device_id"],
                name=row["name"],
                description=row["description"],
                address=DeviceAddress(ip=row["ip"], port=row["port"]) if row["ip"] else None,
                status=DeviceStatus(row["status"]),
                points=points,
            )

    async def list_all(self) -> list[Device]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT device_id FROM devices ORDER BY device_id")
            rows = await cursor.fetchall()
        devices = []
        for row in rows:
            device = await self.get(row["device_id"])
            if device:
                devices.append(device)
        return devices

    async def update_point_value(
        self, device_id: int, point_name: str, value: float | int | bool | str
    ) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE points SET present_value = ? WHERE device_id = ? AND object_name = ?",
                (str(value), device_id, point_name),
            )
            await db.commit()

    async def update_status(self, device_id: int, status: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE devices SET status = ? WHERE device_id = ?",
                (status, device_id),
            )
            await db.commit()


class SqliteEndpointRepository(EndpointRepositoryPort):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def save(self, endpoint: OutboundEndpoint) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO endpoints "
                "(id, url, secret, enabled, event_types, created_at, last_delivery_at, failure_count) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    endpoint.id,
                    endpoint.url,
                    endpoint.secret,
                    1 if endpoint.enabled else 0,
                    json.dumps([et.value for et in endpoint.event_types]),
                    endpoint.created_at.isoformat() if endpoint.created_at else None,
                    endpoint.last_delivery_at.isoformat() if endpoint.last_delivery_at else None,
                    endpoint.failure_count,
                ),
            )
            await db.commit()

    async def get(self, endpoint_id: str) -> OutboundEndpoint | None:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM endpoints WHERE id = ?", (endpoint_id,))
            row = await cursor.fetchone()
            if not row:
                return None
            return self._row_to_endpoint(row)

    async def list_all(self) -> list[OutboundEndpoint]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("SELECT * FROM endpoints ORDER BY created_at")
            rows = await cursor.fetchall()
            return [self._row_to_endpoint(r) for r in rows]

    async def delete(self, endpoint_id: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("DELETE FROM endpoints WHERE id = ?", (endpoint_id,))
            await db.commit()

    async def update_delivery_status(self, endpoint_id: str, success: bool) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            if success:
                await db.execute(
                    "UPDATE endpoints SET last_delivery_at = ?, failure_count = 0 WHERE id = ?",
                    (datetime.now(timezone.utc).isoformat(), endpoint_id),
                )
            else:
                await db.execute(
                    "UPDATE endpoints SET failure_count = failure_count + 1 WHERE id = ?",
                    (endpoint_id,),
                )
            await db.commit()

    @staticmethod
    def _row_to_endpoint(row: aiosqlite.Row) -> OutboundEndpoint:
        event_types_raw = json.loads(row["event_types"]) if row["event_types"] else []
        return OutboundEndpoint(
            id=row["id"],
            url=row["url"],
            secret=row["secret"],
            enabled=bool(row["enabled"]),
            event_types=[EventType(et) for et in event_types_raw],
            created_at=datetime.fromisoformat(row["created_at"]) if row["created_at"] else None,
            last_delivery_at=(
                datetime.fromisoformat(row["last_delivery_at"])
                if row["last_delivery_at"]
                else None
            ),
            failure_count=row["failure_count"],
        )


class SqliteEventLogRepository(EventLogRepositoryPort):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def save(self, event: ReplicationEvent) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO events (id, event_type, timestamp, payload, delivered) "
                "VALUES (?, ?, ?, ?, ?)",
                (
                    event.id,
                    event.event_type.value,
                    event.timestamp.isoformat(),
                    json.dumps(event.payload),
                    1 if event.delivered else 0,
                ),
            )
            await db.commit()

    async def list_recent(self, limit: int = 50) -> list[ReplicationEvent]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            return [
                ReplicationEvent(
                    id=r["id"],
                    event_type=EventType(r["event_type"]),
                    timestamp=datetime.fromisoformat(r["timestamp"]),
                    payload=json.loads(r["payload"]),
                    delivered=bool(r["delivered"]),
                )
                for r in rows
            ]

    async def mark_delivered(self, event_id: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("UPDATE events SET delivered = 1 WHERE id = ?", (event_id,))
            await db.commit()


class SqliteAlarmRepository(AlarmRepositoryPort):
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path

    async def save(self, alarm: Alarm) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "INSERT OR REPLACE INTO alarms "
                "(id, device_id, point_name, severity, message, raised_at, cleared_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (
                    alarm.id,
                    alarm.device_id,
                    alarm.point_name,
                    alarm.severity.value,
                    alarm.message,
                    alarm.raised_at.isoformat(),
                    alarm.cleared_at.isoformat() if alarm.cleared_at else None,
                ),
            )
            await db.commit()

    async def get_active(self) -> list[Alarm]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM alarms WHERE cleared_at IS NULL ORDER BY raised_at DESC"
            )
            rows = await cursor.fetchall()
            return [self._row_to_alarm(r) for r in rows]

    async def clear(self, alarm_id: str) -> None:
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute(
                "UPDATE alarms SET cleared_at = ? WHERE id = ?",
                (datetime.now(timezone.utc).isoformat(), alarm_id),
            )
            await db.commit()

    async def list_recent(self, limit: int = 50) -> list[Alarm]:
        async with aiosqlite.connect(self._db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                "SELECT * FROM alarms ORDER BY raised_at DESC LIMIT ?", (limit,)
            )
            rows = await cursor.fetchall()
            return [self._row_to_alarm(r) for r in rows]

    @staticmethod
    def _row_to_alarm(row: aiosqlite.Row) -> Alarm:
        return Alarm(
            id=row["id"],
            device_id=row["device_id"],
            point_name=row["point_name"],
            severity=AlarmSeverity(row["severity"]),
            message=row["message"],
            raised_at=datetime.fromisoformat(row["raised_at"]),
            cleared_at=datetime.fromisoformat(row["cleared_at"]) if row["cleared_at"] else None,
        )
