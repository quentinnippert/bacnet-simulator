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
    description = "Periodically raises and clears a high supply air temperature alarm on AHU-01."

    def default_parameters(self) -> list[ScenarioParameter]:
        return [
            ScenarioParameter(name="alarm_duration", description="Alarm active duration (s)", default=15),
            ScenarioParameter(name="clear_duration", description="Clear duration (s)", default=20),
            ScenarioParameter(name="high_temp", description="High temperature value", default=35.0),
            ScenarioParameter(name="normal_temp", description="Normal temperature value", default=22.5),
        ]

    async def run(self) -> None:
        alarm_dur = float(self._parameters[0].value)
        clear_dur = float(self._parameters[1].value)
        high_temp = float(self._parameters[2].value)
        normal_temp = float(self._parameters[3].value)

        while self.is_running:
            alarm_id = str(uuid.uuid4())

            # Raise alarm
            try:
                await self._device_service.write_point_by_name(
                    1001, "AHU-01/SupplyAirTemp", high_temp
                )
            except Exception:
                pass

            await self._event_publisher.publish(
                AlarmRaised(
                    alarm_id=alarm_id,
                    device_id=1001,
                    point_name="AHU-01/SupplyAirTemp",
                    severity=AlarmSeverity.HIGH,
                    message=f"Supply air temperature exceeded threshold: {high_temp}°C",
                )
            )
            await asyncio.sleep(alarm_dur)

            if not self.is_running:
                break

            # Clear alarm
            try:
                await self._device_service.write_point_by_name(
                    1001, "AHU-01/SupplyAirTemp", normal_temp
                )
            except Exception:
                pass

            await self._event_publisher.publish(
                AlarmCleared(
                    alarm_id=alarm_id,
                    device_id=1001,
                    point_name="AHU-01/SupplyAirTemp",
                )
            )
            await asyncio.sleep(clear_dur)
