# Scenarios

Scenarios are ready-made simulations that change device values or availability over time. Use them to exercise a BACnet client, dashboard, alarm workflow, or integration without manually changing every point.

## Quick start

Start the simulator, then open the [dashboard](http://localhost:8080/ui) and choose **Scenarios**. Each scenario shows its current status and parameters. Edit the values and choose **Start**; choose **Stop** on a running scenario. The page refreshes scenario state automatically.

You can do the same through the REST API. First list available scenarios and their parameters:

```bash
curl http://localhost:8080/api/scenarios
```

Start the compressed day/night cycle with a one-minute cycle and updates every two seconds:

```bash
curl -X POST http://localhost:8080/api/scenarios/hvac_day_cycle/start \
  -H 'Content-Type: application/json' \
  -d '{"params":{"cycle_seconds":60,"interval":2}}'
```

The start response includes the scenario status and parameter values. Check status and any runtime error with `GET /api/scenarios`; stop it when you are done:

```bash
curl http://localhost:8080/api/scenarios
curl -X POST http://localhost:8080/api/scenarios/hvac_day_cycle/stop
```

For scenarios with no custom settings, omit the request body:

```bash
curl -X POST http://localhost:8080/api/scenarios/hvac_day_cycle/start
```

In PowerShell, use `curl.exe` in place of `curl` if `curl` resolves to the PowerShell web-request alias. If Basic authentication is configured, include the credentials with your HTTP client's authentication option.

## Choose a scenario

| Scenario ID | Use it to… | What happens |
|---|---|---|
| `hvac_day_cycle` | Exercise normal changing HVAC values across several devices | Repeats an illustrative, compressed 24-hour day/night profile. Outdoor temperature, setpoints, valves, fan speed, occupancy, damper position, and CO2 change on each update. |
| `cleanroom_ahu` | Demonstrate the unit-only supply AHU sequence | Sets supply fan speed, controls supply temperature with coil valves, opens the intake damper, estimates fan power, and shuts down on fan fault or fire alarm. |
| `seal_ahu` | Simulate the documented SEAL LHBG01 air handling unit | Runs the weekday fan schedule and models the TF1 supply fan, P1 heating pump, SV21 heating valve, GT11/GT81 temperatures, summer/winter pump logic, return-water protection, latched frost shutdown, outdoor humidity/airflow, and estimated MQ41 heat energy. |
| `alarm_cycle` | Test application alarm handling and event/webhook delivery | Forces a selected point to the high temperature, raises an alarm, restores the prior point state, clears the alarm, then repeats after a clear interval. |
| `device_offline` | Test client behavior when a device stops responding | Repeatedly takes one device offline and brings it online. Other devices remain available. |
| `manual_override` | Test a temporary command or priority handling | Holds a selected point at a value, then restores its prior state after the hold duration. This runs once. |

The HVAC profile is illustrative, not a thermodynamic model. It expects the bundled device IDs and point names; a custom inventory missing one of those points cannot run it. The other scenarios accept a target device/point where applicable, but the device and point must exist and support the requested value.

## Parameters

Durations and update intervals are seconds and must be between **0.01 and 86400**. Omit a parameter to use its default. Unknown parameters, invalid types, unsupported values, or unavailable targets are rejected before the scenario starts.

| Scenario ID | Defaults | Behaviour |
|---|---|---|
| `hvac_day_cycle` | `cycle_seconds=120`, `interval=3`, `fan_rated_power_kw=10.0` | Repeating compressed 24h cycle; estimates AHU supply fan power from fan speed |
| `cleanroom_ahu` | `interval=1`, `fan_speed_setpoint_pct=75.0`, `supply_air_setpoint_c=18.0`, `outdoor_air_damper_pct=100.0`, `fan_rated_power_kw=10.0` | Supply AHU fan-speed and temperature control |
| `seal_ahu` | `interval=1`, `day_cycle_seconds=120`, `simulation_start_hour=7`, `simulation_weekday=0`, `simulation_month=1`, `outdoor_air_temp_c=8`, `supply_air_setpoint_c=20`, `fan_speed_setpoint_pct=50`, `minimum_return_water_temp_c=12`, `stopped_return_water_temp_c=20`, `freeze_limit_c=5`, `startup_valve_boost_pct=50`, `summer_start_month=5`, `winter_start_month=10`, `fan_rated_power_kw=10`, `heating_capacity_kw=100` | Document-based LHBG01 sequence; schedule and setpoints can be supplied at scenario start |
| `alarm_cycle` | `device_id=1001`, `point_name=AHU-01/SupplyAirTemp`, `high_temp=35.0`, `alarm_duration=15`, `clear_duration=20` | Hold temperature → raise application alarm → clear and restore → repeat |
| `device_offline` | `device_id=2001`, `offline_duration=15`, `online_duration=30` | Close/reopen target UDP sockets; other devices continue |
| `manual_override` | `device_id=1001`, `point_name=AHU-01/CoolingValve`, `override_value=100.0`, `hold_duration=30` | One hold, then restore |

The HVAC cycle calculates `AHU-01/ElectricalPower` in kW with `fan_rated_power_kw × (fan_speed / 100)^3`. The default 10 kW fan rating is illustrative and can be changed when starting the scenario. This estimates supply-fan power only; it does not calculate total AHU electrical demand or accumulated energy.

`cleanroom_ahu` retains its existing scenario ID but is displayed as Supply AHU Control. It models a fan-speed setpoint, supply-air temperature control, the intake damper command, and fan/fire interlocks without external room-pressure feedback. The SAT response is simplified simulation dynamics, not a tuned PID loop or a physical air-handling model. Filter differential pressure is exposed for BMS alarming; the scenario does not simulate filter loading. External room-pressure and outdoor-humidity points are intentionally absent from the AHU profile. The removed `room_pressure_setpoint_pa` and `outdoor_air_humidity_pct` parameters are rejected; use `fan_speed_setpoint_pct` for fan control. `seal_ahu` keeps outdoor temperature as a simulation boundary-condition parameter, not an AHU sensor point.

`seal_ahu` uses the LHBG01 operating card and control export. It models Monday-Friday operation from 06:00 to 22:00, winter pump operation, summer pump demand from the heating valve, the Monday pump exercise window, supply-air and return-water control, service/external/fire interlocks, and a latched frost trip. The simulation month and clock are parameters so seasonal and schedule behavior can be tested without waiting for real calendar time. Its simplified temperature response and heat-meter calculations are estimates; the source documents do not provide calibrated fan curves, design airflow, or heating capacity, so `heating_capacity_kw` and `fan_rated_power_kw` are assumptions that should be replaced with project values.

For example, shorten the alarm cycle for a quick test:

```bash
curl -X POST http://localhost:8080/api/scenarios/alarm_cycle/start \
  -H 'Content-Type: application/json' \
  -d '{"params":{"high_temp":38,"alarm_duration":5,"clear_duration":5}}'
```

Then inspect active alarms and recent events at `GET /api/alarms?active_only=true` and `GET /api/events`. The alarm is an application-level event; it does not send BACnet intrinsic notifications.

## Lifecycle and interactions

- Scenario parameters are validated before start and stay fixed while running. The next start uses defaults for omitted parameters. Starting an already-running scenario does not start a second copy.
- `hvac_day_cycle`, `alarm_cycle`, and `device_offline` repeat until stopped. `manual_override` completes after its hold duration and changes to `stopped`.
- Stop waits for cancellation and cleanup. It restores an override, clears an active application alarm, or brings an offline target back online, as applicable.
- Scenarios publish lifecycle events. Runtime failures set status to `error`, populate the scenario's `error` field, and emit `scenario_failed`.
- Multiple scenarios can run together when their point/device ownership does not conflict. Application scenarios yield to each other's owned points; a higher-priority BACnet command can still determine the effective value.
- A device taken offline retains its values and priorities when it reconnects. BACnet COV subscribers may need to resubscribe.

## Behaviour and limits

| Topic | Rule |
|---|---|
| HVAC model | Monotonic time; outdoor 8–32°C (min 03:00, max 15:00); occupied 07:00–19:00 |
| HVAC targets | Bundled names/IDs checked on start; drives temperatures, valves, fans, occupancy, damper and CO2; offline devices skipped |
| Custom devices | HVAC does not infer arbitrary point names; model is illustrative, not thermodynamic |
| Alarm cleanup | Stop clears the active alarm; process restart clears leftover alarms |
| Alarm protocol | Application/webhook events only; no BACnet intrinsic notifications |
| Override ownership | One explicit owner per point; other application scenarios yield; higher BACnet priorities still win |
| Restoration | Previous priority-8 slot or simulated input source; later writes at that slot are preserved, even at the same value |
| Offline cleanup | Stop restores an offline target; values/priorities survive reconnect, COV clients must resubscribe |
| Conflicts | Stop overrides before taking a device offline; runtime conflicts/failures expose `error` and emit `scenario_failed` |

**Migration:** `normal_temp` and `original_value` were removed; restoration uses captured state. Binary/multistate overrides use their JSON types through the API; the dashboard override field is numeric (analog).
