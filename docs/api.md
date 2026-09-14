# REST API

Interactive schema: `/docs`; machine-readable schema: `/openapi.json`. Configured Basic authentication protects all routes. Mutating browser requests from other origins are rejected.

| Method | Path | Behaviour |
|---|---|---|
| GET | `/api/health` | Health, online count and errors; 503 when degraded |
| GET | `/api/devices` | Inventory, addresses, status and point counts |
| GET | `/api/devices/{id}` | Effective points, units, COV thresholds and state labels |
| PUT | `/api/devices/{id}/points` | Write/relinquish and return the effective point |
| GET | `/api/scenarios` | Scenarios, parameters, states and last errors |
| POST | `/api/scenarios/{id}/start` | Validate parameters and start; idempotent while running |
| POST | `/api/scenarios/{id}/stop` | Await cancellation and cleanup |
| GET | `/api/endpoints` | Webhook registrations without secrets |
| POST | `/api/endpoints` | Register an allowed URL; returns the secret once |
| DELETE | `/api/endpoints/{id}` | Idempotent removal, including pending deliveries; empty 204 |
| POST | `/api/endpoints/{id}/test` | Synchronous connectivity test; 502 on delivery failure |
| GET | `/api/events` | Recent event history |
| GET | `/api/alarms` | Recent alarms, optional `active_only=true` |
| GET | `/api/deliveries` | Per-recipient attempts, state, next retry and last error |

Event/alarm limits default to 50; delivery limits default to 100. `limit` must be between 1 and 500. The active alarm query returns all active alarms.

## Point writes

By name:

```json
{"point_name":"AHU-01/CoolingValve","value":80,"priority":16}
```

Or by identifier:

```json
{"object_type":"analogOutput","object_instance":1,"value":80}
```

| Input | Rule |
|---|---|
| Target | Exactly one form: name **or** type + instance |
| Priority | 1–16 except reserved 6; default 16 |
| `null` | Release the selected slot on a commandable point |
| Binary / multistate | JSON boolean / integer in configured state range |
| Analog | Finite 32-bit Real; percentages 0–100 |
| Sensor input | HTTP drives the simulated source; native Out_Of_Service holds the BACnet test value until rejoining |
| Response | Effective value; a higher priority may prevail; conflicting scenario ownership returns 409 |

Native BACnet input writes require Out_Of_Service=true. [Protocol contract](bacnet-profile.md).

## Scenarios

```json
{"params":{"cycle_seconds":60,"interval":2}}
```

- Unknown parameters, invalid types or durations outside 0.01–86400 seconds fail before start.
- Parameters stay fixed until stop/restart; omitted parameters revert to defaults.
- Response: `status`, `parameters`, `error`; runtime failures emit `scenario_failed`.

## Errors

| Status | Meaning |
|---|---|
| 401 | Missing or invalid Basic credentials |
| 403 | Cross-origin browser command |
| 404 | Missing device, point, scenario or tested endpoint |
| 409 | Conflicting ownership/state transition |
| 422 | Invalid parameters, values, URL or unknown fields |
| 503 | Device unavailable or health degraded |
| 500 | Unexpected server/storage failure; not disguised as an auth failure |

A protocol mutation can precede a persistence failure. On an ambiguous failed write, read the effective point before retrying.
