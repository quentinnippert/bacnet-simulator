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
            ScenarioParameter(
                name="cycle_seconds", description="Full cycle duration in seconds", default=120
            ),
            ScenarioParameter(name="interval", description="Update interval in seconds", default=3),
        ]

    def validate(self) -> None:
        required = {
            1001: [
                "SupplyAirTempSetpoint",
                "SupplyAirTemp",
                "ReturnAirTemp",
                "CoolingValve",
                "HeatingValve",
                "FanSpeed",
            ],
            2001: ["RoomTemp", "OccupancySensor"],
            2002: ["RoomTemp", "OccupancySensor"],
            3001: ["SpaceTemp", "Occupancy"],
            4001: ["ZoneTemp", "DamperPosition"],
            5001: ["OutdoorTemp"],
            5002: ["CO2Level"],
        }
        names = {
            1001: "AHU-01",
            2001: "FCU-01",
            2002: "FCU-02",
            3001: "TSTAT-01",
            4001: "ZC-01",
            5001: "OAT-01",
            5002: "CO2-01",
        }
        for device_id, points in required.items():
            for point in points:
                self.require_point(device_id, f"{names[device_id]}/{point}")

    async def run(self) -> None:
        cycle_s = float(self.parameter("cycle_seconds"))
        interval = float(self.parameter("interval"))
        started = asyncio.get_running_loop().time()

        while self.is_running:
            t = asyncio.get_running_loop().time() - started
            phase = (t % cycle_s) / cycle_s  # 0..1 representing 24h
            hour = phase * 24

            # Outdoor temp: min 8C at 3am, max 32C at 15h
            outdoor_temp = 20 + 12 * math.sin((hour - 9) * math.pi / 12)

            # Occupied hours: 7-19
            occupied = 7 <= hour <= 19
            supply_setpoint = 22.0 if occupied else 18.0
            fan_speed = 75.0 if occupied else 30.0
            cooling_valve = max(0, min(100, (outdoor_temp - 22) * 5)) if occupied else 0.0
            heating_valve = (
                max(0, min(100, (18 - outdoor_temp) * 5))
                if not occupied and outdoor_temp < 18
                else 0.0
            )

            # Room temps drift based on outdoor
            room_temp = supply_setpoint + (outdoor_temp - supply_setpoint) * 0.1

            # Write to AHU-01
            await self.write(5001, "OAT-01/OutdoorTemp", round(outdoor_temp, 1))
            await self.write(1001, "AHU-01/SupplyAirTempSetpoint", supply_setpoint)
            await self.write(
                1001,
                "AHU-01/SupplyAirTemp",
                round(supply_setpoint + (outdoor_temp - supply_setpoint) * 0.05, 1),
            )
            await self.write(1001, "AHU-01/ReturnAirTemp", round(room_temp + 1.5, 1))
            await self.write(1001, "AHU-01/CoolingValve", round(cooling_valve, 1))
            await self.write(1001, "AHU-01/HeatingValve", round(heating_valve, 1))
            await self.write(1001, "AHU-01/FanSpeed", round(fan_speed, 1))

            # FCUs follow
            await self.write(2001, "FCU-01/RoomTemp", round(room_temp - 0.5, 1))
            await self.write(2002, "FCU-02/RoomTemp", round(room_temp + 0.3, 1))
            await self.write(2001, "FCU-01/OccupancySensor", occupied)
            await self.write(2002, "FCU-02/OccupancySensor", occupied)

            # Thermostat
            await self.write(3001, "TSTAT-01/SpaceTemp", round(room_temp, 1))
            await self.write(3001, "TSTAT-01/Occupancy", occupied)

            # Zone controller
            await self.write(4001, "ZC-01/ZoneTemp", round(room_temp + 0.2, 1))
            damper = 65.0 if occupied else 20.0
            await self.write(4001, "ZC-01/DamperPosition", damper)

            # CO2 sensor
            co2 = 400 + (occupied and 300 * math.sin(phase * math.pi) or 0)
            await self.write(5002, "CO2-01/CO2Level", round(co2, 0))

            await asyncio.sleep(interval)
