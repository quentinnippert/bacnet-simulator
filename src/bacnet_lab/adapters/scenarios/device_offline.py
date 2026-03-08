from __future__ import annotations

import asyncio

from bacnet_lab.adapters.scenarios.base import BaseScenario
from bacnet_lab.domain.enums import DeviceStatus
from bacnet_lab.domain.models.scenario import ScenarioParameter


class DeviceOfflineScenario(BaseScenario):
    id = "device_offline"
    name = "Temporary Device Offline"
    description = "Simulates a device going offline temporarily, then recovering."

    def default_parameters(self) -> list[ScenarioParameter]:
        return [
            ScenarioParameter(name="device_id", description="Target device ID", default=2001),
            ScenarioParameter(name="offline_duration", description="Offline duration (s)", default=15),
            ScenarioParameter(name="online_duration", description="Online duration (s)", default=30),
        ]

    async def run(self) -> None:
        device_id = int(self._parameters[0].value)
        offline_dur = float(self._parameters[1].value)
        online_dur = float(self._parameters[2].value)

        while self.is_running:
            # Go offline
            try:
                await self._device_service.set_device_status(device_id, DeviceStatus.OFFLINE)
            except Exception:
                pass

            await asyncio.sleep(offline_dur)
            if not self.is_running:
                break

            # Come back online
            try:
                await self._device_service.set_device_status(device_id, DeviceStatus.ONLINE)
            except Exception:
                pass

            await asyncio.sleep(online_dur)
