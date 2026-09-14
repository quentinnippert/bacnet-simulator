# Scenarios

Start/stop from the dashboard or API. Parameters are validated before start, fixed during a run and reset to defaults on restart. Stop waits for cleanup; transitions emit events.

```bash
curl -X POST http://localhost:8080/api/scenarios/hvac_day_cycle/start \
  -H 'Content-Type: application/json' \
  -d '{"params":{"cycle_seconds":60,"interval":2}}'
curl -X POST http://localhost:8080/api/scenarios/hvac_day_cycle/stop
```

## Parameters

All durations/intervals are seconds, from **0.01 to 86400**.

| Scenario ID | Defaults | Behaviour |
|---|---|---|
| `hvac_day_cycle` | `cycle_seconds=120`, `interval=3` | Repeating compressed 24h cycle |
| `alarm_cycle` | `device_id=1001`, `point_name=AHU-01/SupplyAirTemp`, `high_temp=35.0`, `alarm_duration=15`, `clear_duration=20` | Hold temperature → raise application alarm → clear and restore → repeat |
| `device_offline` | `device_id=2001`, `offline_duration=15`, `online_duration=30` | Close/reopen target UDP sockets; other devices continue |
| `manual_override` | `device_id=1001`, `point_name=AHU-01/CoolingValve`, `override_value=100.0`, `hold_duration=30` | One hold, then restore |

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

Multiple scenarios may run concurrently within these ownership rules.

**Migration:** `normal_temp` and `original_value` were removed; restoration uses captured state. Binary/multistate overrides use their JSON types through the API; the dashboard override field is numeric (analog).
