from __future__ import annotations

import asyncio

from bacnet_lab.adapters.scenarios.base import BaseScenario
from bacnet_lab.domain.models.scenario import ScenarioParameter


class ManualOverrideScenario(BaseScenario):
    id = "manual_override"
    name = "Manual Override"
    description = "Overrides a specific point to a fixed value, then releases after a duration."

    def default_parameters(self) -> list[ScenarioParameter]:
        return [
            ScenarioParameter(name="device_id", description="Target device ID", default=1001),
            ScenarioParameter(name="point_name", description="Point name to override", default="AHU-01/CoolingValve"),
            ScenarioParameter(name="override_value", description="Override value", default=100.0),
            ScenarioParameter(name="original_value", description="Original value to restore", default=45.0),
            ScenarioParameter(name="hold_duration", description="Hold duration (s)", default=30),
        ]

    async def run(self) -> None:
        device_id = int(self._parameters[0].value)
        point_name = str(self._parameters[1].value)
        override_val = float(self._parameters[2].value)
        original_val = float(self._parameters[3].value)
        hold_dur = float(self._parameters[4].value)

        # Apply override
        try:
            await self._device_service.write_point_by_name(device_id, point_name, override_val)
        except Exception:
            pass

        await asyncio.sleep(hold_dur)

        # Release override
        if self.is_running:
            try:
                await self._device_service.write_point_by_name(device_id, point_name, original_val)
            except Exception:
                pass
