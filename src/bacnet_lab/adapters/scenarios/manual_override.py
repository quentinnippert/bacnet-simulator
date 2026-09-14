from __future__ import annotations

import asyncio

from bacnet_lab.adapters.scenarios.base import BaseScenario
from bacnet_lab.domain.models.scenario import ScenarioParameter


class ManualOverrideScenario(BaseScenario):
    id = "manual_override"
    name = "Manual Override"
    description = "Hold a point using priority 8, then relinquish it (or restore an input)."

    def default_parameters(self) -> list[ScenarioParameter]:
        return [
            ScenarioParameter("device_id", "Target device ID", 1001),
            ScenarioParameter("point_name", "Target point", "AHU-01/CoolingValve"),
            ScenarioParameter("override_value", "Value to force", 100.0),
            ScenarioParameter("hold_duration", "Duration in seconds", 30),
        ]

    def validate(self) -> None:
        self.require_point(
            self.parameter("device_id"),
            self.parameter("point_name"),
            self.parameter("override_value"),
        )

    async def run(self) -> None:
        async with self._device_service.override(
            self.parameter("device_id"),
            self.parameter("point_name"),
            self.parameter("override_value"),
            self.id,
        ):
            await asyncio.sleep(self.parameter("hold_duration"))
