from __future__ import annotations

import asyncio
import math

from bacnet_lab.adapters.scenarios.base import BaseScenario
from bacnet_lab.domain.models.scenario import ScenarioParameter


class HvacDayCycleScenario(BaseScenario):
    id = "hvac_day_cycle"
    name = "HVAC Day/Night Cycle"
    description = "Simulates a compressed 24h HVAC cycle: temperature, valve positions, and fan speeds vary over time."

    def default_parameters(self) -> list[ScenarioParameter]:
        return [
            ScenarioParameter(name="cycle_seconds", description="Full cycle duration in seconds", default=120),
            ScenarioParameter(name="interval", description="Update interval in seconds", default=3),
        ]

    async def run(self) -> None:
        cycle_s = float(self._parameters[0].value)
        interval = float(self._parameters[1].value)
        t = 0.0

        while self.is_running:
            phase = (t % cycle_s) / cycle_s  # 0..1 representing 24h
            hour = phase * 24

            # Outdoor temp: min 8C at 5am, max 32C at 15h
            outdoor_temp = 20 + 12 * math.sin((hour - 9) * math.pi / 12)

            # Occupied hours: 7-19
            occupied = 7 <= hour <= 19
            supply_setpoint = 22.0 if occupied else 18.0
            fan_speed = 75.0 if occupied else 30.0
            cooling_valve = max(0, min(100, (outdoor_temp - 22) * 5)) if occupied else 0.0
            heating_valve = max(0, min(100, (18 - outdoor_temp) * 5)) if not occupied and outdoor_temp < 18 else 0.0

            # Room temps drift based on outdoor
            room_temp = supply_setpoint + (outdoor_temp - supply_setpoint) * 0.1

            # Write to AHU-01
            try:
                ds = self._device_service
                await ds.write_point_by_name(5001, "OAT-01/OutdoorTemp", round(outdoor_temp, 1))
                await ds.write_point_by_name(1001, "AHU-01/SupplyAirTempSetpoint", supply_setpoint)
                await ds.write_point_by_name(1001, "AHU-01/SupplyAirTemp", round(supply_setpoint + (outdoor_temp - supply_setpoint) * 0.05, 1))
                await ds.write_point_by_name(1001, "AHU-01/ReturnAirTemp", round(room_temp + 1.5, 1))
                await ds.write_point_by_name(1001, "AHU-01/CoolingValve", round(cooling_valve, 1))
                await ds.write_point_by_name(1001, "AHU-01/HeatingValve", round(heating_valve, 1))
                await ds.write_point_by_name(1001, "AHU-01/FanSpeed", round(fan_speed, 1))

                # FCUs follow
                await ds.write_point_by_name(2001, "FCU-01/RoomTemp", round(room_temp - 0.5, 1))
                await ds.write_point_by_name(2002, "FCU-02/RoomTemp", round(room_temp + 0.3, 1))
                await ds.write_point_by_name(2001, "FCU-01/OccupancySensor", occupied)
                await ds.write_point_by_name(2002, "FCU-02/OccupancySensor", occupied)

                # Thermostat
                await ds.write_point_by_name(3001, "TSTAT-01/SpaceTemp", round(room_temp, 1))
                await ds.write_point_by_name(3001, "TSTAT-01/Occupancy", occupied)

                # Zone controller
                await ds.write_point_by_name(4001, "ZC-01/ZoneTemp", round(room_temp + 0.2, 1))
                damper = 65.0 if occupied else 20.0
                await ds.write_point_by_name(4001, "ZC-01/DamperPosition", damper)

                # CO2 sensor
                co2 = 400 + (occupied and 300 * math.sin(phase * math.pi) or 0)
                await ds.write_point_by_name(5002, "CO2-01/CO2Level", round(co2, 0))
            except Exception:
                pass

            t += interval
            await asyncio.sleep(interval)
