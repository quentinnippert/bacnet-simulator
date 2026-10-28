from __future__ import annotations

import asyncio
import math

from bacnet_lab.adapters.scenarios.base import BaseScenario
from bacnet_lab.domain.errors import ValidationError
from bacnet_lab.domain.models.scenario import ScenarioParameter


class SealAhuScenario(BaseScenario):
    id = "seal_ahu"
    name = "AHU with supply air only"
    description = (
        "Simulates the documented supply fan, heating pump and valve, return-water/frost "
        "protection, operating schedule, and heat meter."
    )

    def default_parameters(self) -> list[ScenarioParameter]:
        return [
            ScenarioParameter(name="interval", description="Update interval in seconds", default=1.0),
            ScenarioParameter(
                name="day_cycle_seconds",
                description="Simulated 24-hour day duration in seconds",
                default=120.0,
            ),
            ScenarioParameter(
                name="simulation_start_hour",
                description="Hour of day when the simulation starts",
                default=7.0,
            ),
            ScenarioParameter(
                name="simulation_weekday",
                description="Starting weekday, Monday=0 through Sunday=6",
                default=0,
            ),
            ScenarioParameter(
                name="simulation_month", description="Month used for summer/winter mode", default=1
            ),
            ScenarioParameter(
                name="outdoor_air_temp_c", description="Outdoor air temperature in Celsius", default=8.0
            ),
            ScenarioParameter(
                name="outdoor_air_humidity_pct",
                description="Outdoor relative humidity in percent",
                default=70.0,
            ),
            ScenarioParameter(
                name="supply_air_setpoint_c",
                description="Supply air temperature target in Celsius",
                default=20.0,
            ),
            ScenarioParameter(
                name="fan_speed_setpoint_pct",
                description="Supply fan speed target in percent",
                default=50.0,
            ),
            ScenarioParameter(
                name="minimum_return_water_temp_c",
                description="Return-water minimum while running in Celsius",
                default=12.0,
            ),
            ScenarioParameter(
                name="stopped_return_water_temp_c",
                description="Return-water target while stopped in Celsius",
                default=20.0,
            ),
            ScenarioParameter(
                name="freeze_limit_c",
                description="Frost protection trip temperature in Celsius",
                default=5.0,
            ),
            ScenarioParameter(
                name="startup_valve_boost_pct",
                description="Heating valve opening during winter startup in percent",
                default=50.0,
            ),
            ScenarioParameter(
                name="summer_start_month", description="First summer-mode month", default=5
            ),
            ScenarioParameter(
                name="winter_start_month", description="First winter-mode month", default=10
            ),
            ScenarioParameter(
                name="fan_rated_power_kw",
                description="Assumed rated supply fan power in kW",
                default=10.0,
            ),
            ScenarioParameter(
                name="heating_capacity_kw",
                description="Assumed heating capacity used by the meter model in kW",
                default=100.0,
            ),
        ]

    def validate(self) -> None:
        required = (
            "SupplyAirTemp",
            "SupplyAirTempSetpoint",
            "SupplyFanEnable",
            "FanRunStatus",
            "FanFault",
            "FanSpeed",
            "FanSpeedFeedback",
            "OutdoorAirDamper",
            "ReturnWaterTemp",
            "ReturnWaterTempSetpoint",
            "ReturnWaterMinimumSetpoint",
            "OutdoorAirHumidity",
            "IntakeAirflow",
            "HeatingValve",
            "HeatingPumpEnable",
            "HeatingPumpRunStatus",
            "HeatingPumpFault",
            "ServiceSwitch",
            "ExternalStop",
            "FireAlarmStatus",
            "FreezeProtectionAlarm",
            "ReturnWaterControlActive",
            "HeatingPower",
            "HeatingEnergy",
            "ElectricalPower",
        )
        for point_name in required:
            self.require_point(1001, f"AHU-01/{point_name}")

        for name in (
            "simulation_weekday",
            "simulation_month",
            "summer_start_month",
            "winter_start_month",
        ):
            if type(self.parameter(name)) is not int:
                raise ValidationError(f"{name} must be an integer")
        if not 0 <= self.parameter("simulation_weekday") <= 6:
            raise ValidationError("simulation_weekday must be between 0 and 6")
        for name in ("simulation_month", "summer_start_month", "winter_start_month"):
            if not 1 <= self.parameter(name) <= 12:
                raise ValidationError(f"{name} must be between 1 and 12")
        if self.parameter("summer_start_month") >= self.parameter("winter_start_month"):
            raise ValidationError("summer_start_month must be before winter_start_month")
        if not 0 <= self.parameter("simulation_start_hour") < 24:
            raise ValidationError("simulation_start_hour must be between 0 and 24")
        if not -40 <= self.parameter("outdoor_air_temp_c") <= 60:
            raise ValidationError("outdoor_air_temp_c must be between -40 and 60 Celsius")
        if not 0 <= self.parameter("outdoor_air_humidity_pct") <= 100:
            raise ValidationError("outdoor_air_humidity_pct must be between 0 and 100 percent")
        if not 5 <= self.parameter("supply_air_setpoint_c") <= 35:
            raise ValidationError("supply_air_setpoint_c must be between 5 and 35 Celsius")
        for name in ("fan_speed_setpoint_pct", "startup_valve_boost_pct"):
            if not 0 <= self.parameter(name) <= 100:
                raise ValidationError(f"{name} must be between 0 and 100 percent")
        for name in (
            "minimum_return_water_temp_c",
            "stopped_return_water_temp_c",
            "freeze_limit_c",
        ):
            if not -20 <= self.parameter(name) <= 60:
                raise ValidationError(f"{name} must be between -20 and 60 Celsius")
        for name in ("fan_rated_power_kw", "heating_capacity_kw"):
            if self.parameter(name) <= 0:
                raise ValidationError(f"{name} must be greater than zero")

    async def run(self) -> None:
        interval = float(self.parameter("interval"))
        day_cycle_seconds = float(self.parameter("day_cycle_seconds"))
        started = asyncio.get_running_loop().time()
        last_tick = started
        return_temp = float(
            self._device_service.point(1001, "AHU-01/ReturnWaterTemp").present_value
        )
        supply_temp = float(
            self._device_service.point(1001, "AHU-01/SupplyAirTemp").present_value
        )
        energy_kwh = float(
            self._device_service.point(1001, "AHU-01/HeatingEnergy").present_value
        )
        freeze_latched = False
        fan_was_running = False

        while self.is_running:
            now = asyncio.get_running_loop().time()
            elapsed = now - started
            simulated_hours = float(self.parameter("simulation_start_hour")) + (
                elapsed * 24 / day_cycle_seconds
            )
            hour = simulated_hours % 24
            weekday = (
                int(self.parameter("simulation_weekday")) + math.floor(simulated_hours / 24)
            ) % 7
            month = int(self.parameter("simulation_month"))
            summer_start = int(self.parameter("summer_start_month"))
            winter_start = int(self.parameter("winter_start_month"))
            winter_mode = month < summer_start or month >= winter_start
            occupied = weekday < 5 and 6 <= hour < 22
            pump_exercise = weekday == 0 and 12 <= hour < 12 + 10 / 60

            outdoor_temp = float(self.parameter("outdoor_air_temp_c"))
            humidity = float(self.parameter("outdoor_air_humidity_pct"))
            supply_setpoint = float(self.parameter("supply_air_setpoint_c"))
            return_minimum = float(self.parameter("minimum_return_water_temp_c"))
            stopped_return_setpoint = float(self.parameter("stopped_return_water_temp_c"))
            freeze_limit = float(self.parameter("freeze_limit_c"))

            service_switch = bool(
                self._device_service.point(1001, "AHU-01/ServiceSwitch").present_value
            )
            external_stop = bool(
                self._device_service.point(1001, "AHU-01/ExternalStop").present_value
            )
            fire_alarm = bool(
                self._device_service.point(1001, "AHU-01/FireAlarmStatus").present_value
            )
            fan_fault = bool(self._device_service.point(1001, "AHU-01/FanFault").present_value)
            pump_fault = bool(
                self._device_service.point(1001, "AHU-01/HeatingPumpFault").present_value
            )
            if return_temp <= freeze_limit:
                freeze_latched = True
            if service_switch and return_temp >= freeze_limit + 5:
                freeze_latched = False

            shutdown = service_switch or external_stop or fire_alarm or freeze_latched
            if shutdown:
                valve = max(0.0, min(100.0, (stopped_return_setpoint - return_temp) * 10))
            else:
                valve = max(
                    0.0,
                    min(
                        100.0,
                        (supply_setpoint - outdoor_temp) / 0.3
                        + (supply_setpoint - supply_temp) * 5,
                    ),
                )
                if occupied and winter_mode and not fan_was_running:
                    valve = max(valve, float(self.parameter("startup_valve_boost_pct")))
                if return_temp < return_minimum:
                    valve = max(valve, min(100.0, (return_minimum - return_temp) * 20))

            return_control = not shutdown and return_temp < return_minimum
            pump_requested = winter_mode or valve > 3 or pump_exercise
            pump_running = pump_requested and not shutdown and not pump_fault
            fan_running = (
                occupied
                and not shutdown
                and not fan_fault
                and (not winter_mode or pump_running)
            )
            if not fan_running and not shutdown:
                valve = max(0.0, min(100.0, (stopped_return_setpoint - return_temp) * 10))

            fan_speed = float(self.parameter("fan_speed_setpoint_pct")) if fan_running else 0.0
            damper = 100.0 if fan_running else 0.0
            supply_target = outdoor_temp + valve * 0.3 if fan_running else outdoor_temp
            supply_temp += (supply_target - supply_temp) * 0.2
            return_target = (
                outdoor_temp + 12 + valve * 0.15
                if fan_running
                else outdoor_temp * 0.2 + 8 + valve * 0.25
            )
            return_temp += (return_target - return_temp) * 0.1

            fan_power = float(self.parameter("fan_rated_power_kw")) * (fan_speed / 100) ** 3
            heating_power = (
                float(self.parameter("heating_capacity_kw"))
                * (valve / 100)
                * max(0.0, min(1.0, (supply_temp - return_temp) / 30))
            )
            energy_kwh += heating_power * max(0.0, now - last_tick) / 3600
            last_tick = now

            writes = (
                ("SupplyAirTempSetpoint", supply_setpoint),
                ("SupplyAirTemp", round(supply_temp, 1)),
                ("FanSpeed", round(fan_speed, 1)),
                ("FanSpeedFeedback", round(fan_speed, 1)),
                ("SupplyFanEnable", fan_running),
                ("OutdoorAirDamper", round(damper, 1)),
                ("HeatingValve", round(valve, 1)),
                ("HeatingPumpEnable", pump_running),
                ("ReturnWaterTemp", round(return_temp, 1)),
                ("ReturnWaterTempSetpoint", stopped_return_setpoint),
                ("ReturnWaterMinimumSetpoint", return_minimum),
                ("OutdoorAirHumidity", humidity),
                ("IntakeAirflow", round(fan_speed, 1)),
                ("ReturnWaterControlActive", return_control),
                ("ElectricalPower", round(fan_power, 2)),
                ("HeatingPower", round(heating_power, 2)),
                ("HeatingEnergy", round(energy_kwh, 3)),
                ("FreezeProtectionAlarm", freeze_latched),
                ("FanRunStatus", fan_running),
                ("HeatingPumpRunStatus", pump_running),
            )
            for name, value in writes:
                await self.write(1001, f"AHU-01/{name}", value)

            fan_was_running = fan_running
            await asyncio.sleep(interval)