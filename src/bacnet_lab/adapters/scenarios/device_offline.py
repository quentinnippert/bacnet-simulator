from __future__ import annotations

import asyncio

from bacnet_lab.adapters.scenarios.base import BaseScenario
from bacnet_lab.domain.enums import DeviceStatus
from bacnet_lab.domain.errors import NotFoundError, UnavailableError
from bacnet_lab.domain.models.scenario import ScenarioParameter


class DeviceOfflineScenario(BaseScenario):
    id = "device_offline"
    name = "Temporary Device Offline"
    description = "Close the device UDP sockets temporarily, then restore communication."

    def default_parameters(self) -> list[ScenarioParameter]:
        return [
            ScenarioParameter("device_id", "Target device ID", 2001),
            ScenarioParameter("offline_duration", "Offline duration in seconds", 15),
            ScenarioParameter("online_duration", "Online duration in seconds", 30),
        ]

    def validate(self) -> None:
        device = self._device_service.get_in_memory_device(self.parameter("device_id"))
        if device is None:
            raise NotFoundError("Target device not found")
        if device.status != DeviceStatus.ONLINE:
            raise UnavailableError("Target device must be online")

    async def run(self) -> None:
        device_id = self.parameter("device_id")
        try:
            while self.is_running:
                await self._device_service.set_device_status(device_id, DeviceStatus.OFFLINE)
                await asyncio.sleep(self.parameter("offline_duration"))
                await self._device_service.set_device_status(device_id, DeviceStatus.ONLINE)
                await asyncio.sleep(self.parameter("online_duration"))
        finally:
            device = self._device_service.get_in_memory_device(device_id)
            if device.status == DeviceStatus.OFFLINE:
                await self._device_service.set_device_status(device_id, DeviceStatus.ONLINE)
