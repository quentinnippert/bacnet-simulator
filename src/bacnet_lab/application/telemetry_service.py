from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from bacnet_lab.domain.events import PointValueChanged
from bacnet_lab.domain.models.event import TelemetrySnapshot
from bacnet_lab.domain.value_objects import PointValue
from bacnet_lab.ports.event_publisher import EventPublisherPort

logger = logging.getLogger(__name__)


class TelemetryService:
    def __init__(
        self,
        event_publisher: EventPublisherPort,
        snapshot_interval: float = 30.0,
    ) -> None:
        self._events = event_publisher
        self._snapshot_interval = snapshot_interval
        self._last_values: dict[str, PointValue] = {}
        self._task: asyncio.Task | None = None
        self._device_service = None

    def set_device_service(self, device_service: object) -> None:
        self._device_service = device_service

    async def start(self) -> None:
        self._task = asyncio.create_task(self._snapshot_loop())
        logger.info("Telemetry service started (interval=%ss)", self._snapshot_interval)

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Telemetry service stopped")

    async def check_cov(self, device_id: int, point_name: str, value: PointValue, cov_increment: float) -> None:
        key = f"{device_id}/{point_name}"
        old = self._last_values.get(key)
        if old is None:
            self._last_values[key] = value
            return
        if isinstance(value, (int, float)) and isinstance(old, (int, float)):
            if cov_increment > 0 and abs(float(value) - float(old)) >= cov_increment:
                self._last_values[key] = value
                await self._events.publish(
                    PointValueChanged(
                        device_id=device_id,
                        point_name=point_name,
                        old_value=old,
                        new_value=value,
                    )
                )
        elif value != old:
            self._last_values[key] = value
            await self._events.publish(
                PointValueChanged(
                    device_id=device_id,
                    point_name=point_name,
                    old_value=old,
                    new_value=value,
                )
            )

    async def _snapshot_loop(self) -> None:
        while True:
            await asyncio.sleep(self._snapshot_interval)
            if not self._device_service:
                continue
            try:
                devices = self._device_service.get_all_in_memory_devices()
                for device in devices:
                    points_data = {}
                    for point in device.points:
                        points_data[point.object_name] = point.present_value
                    TelemetrySnapshot(
                        timestamp=datetime.now(timezone.utc),
                        device_id=device.device_id,
                        points=points_data,
                    )
            except Exception as e:
                logger.error("Telemetry snapshot error: %s", e)
