from __future__ import annotations

import asyncio
import uuid

from bacnet_lab.adapters.scenarios.base import BaseScenario
from bacnet_lab.domain.enums import AlarmSeverity
from bacnet_lab.domain.events import AlarmCleared, AlarmRaised
from bacnet_lab.domain.models.scenario import ScenarioParameter


class AlarmScenario(BaseScenario):
    id = "alarm_cycle"
    name = "Cyclic High Temperature Alarm"
    description = "Raise an application alarm while holding a supply temperature, then restore it."

    def default_parameters(self) -> list[ScenarioParameter]:
        return [
            ScenarioParameter("device_id", "Target device ID", 1001),
            ScenarioParameter("point_name", "Target temperature", "AHU-01/SupplyAirTemp"),
            ScenarioParameter("alarm_duration", "Alarm duration in seconds", 15),
            ScenarioParameter("clear_duration", "Clear duration in seconds", 20),
            ScenarioParameter("high_temp", "Alarm temperature", 35.0),
        ]

    def validate(self) -> None:
        self.require_point(
            self.parameter("device_id"), self.parameter("point_name"), self.parameter("high_temp")
        )

    async def run(self) -> None:
        device_id, point_name = self.parameter("device_id"), self.parameter("point_name")
        while self.is_running:
            async with self._device_service.override(
                device_id, point_name, self.parameter("high_temp"), self.id
            ):
                alarm_id = str(uuid.uuid4())
                try:
                    await self._event_publisher.publish(
                        AlarmRaised(
                            alarm_id=alarm_id,
                            device_id=device_id,
                            point_name=point_name,
                            severity=AlarmSeverity.HIGH,
                            message=f"Temperature forced to {self.parameter('high_temp')}°C",
                        )
                    )
                    await asyncio.sleep(self.parameter("alarm_duration"))
                finally:
                    await self._event_publisher.publish(
                        AlarmCleared(alarm_id=alarm_id, device_id=device_id, point_name=point_name)
                    )
            await asyncio.sleep(self.parameter("clear_duration"))
