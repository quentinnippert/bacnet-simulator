from __future__ import annotations

import asyncio
import logging

from bacnet_lab.application.device_service import DeviceService
from bacnet_lab.domain.enums import DeviceStatus
from bacnet_lab.domain.events import TelemetrySnapshotTaken
from bacnet_lab.ports.event_publisher import EventPublisherPort

logger = logging.getLogger(__name__)


class TelemetryService:
    def __init__(
        self,
        event_publisher: EventPublisherPort,
        snapshot_interval: float = 300,
        sync_interval: float = 0.25,
    ) -> None:
        self._events, self._snapshot_interval = event_publisher, snapshot_interval
        self._sync_interval = sync_interval
        self._task: asyncio.Task | None = None
        self._device_service: DeviceService | None = None
        self.error: str | None = None

    def set_device_service(self, device_service: DeviceService) -> None:
        self._device_service = device_service

    async def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="telemetry")

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        next_snapshot = loop.time() + self._snapshot_interval
        while True:
            try:
                if self._device_service is None:
                    raise RuntimeError("Device service not configured")
                devices = await self._device_service.list_devices()
                if loop.time() >= next_snapshot:
                    for device in devices:
                        if device.status == DeviceStatus.ONLINE:
                            await self._events.publish(
                                TelemetrySnapshotTaken(
                                    device_id=device.device_id,
                                    points={p.object_name: p.present_value for p in device.points},
                                )
                            )
                    next_snapshot = loop.time() + self._snapshot_interval
                self.error = None
            except Exception as exc:
                self.error = str(exc)
                logger.exception("Telemetry synchronization failed")
            await asyncio.sleep(self._sync_interval)
