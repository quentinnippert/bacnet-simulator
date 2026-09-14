# Webhooks

## Register a receiver

1. Add its trusted hostname/IP to `BACNET_LAB_WEBHOOK_ALLOWED_HOSTS` (default: `localhost,127.0.0.1`).
2. `POST /api/endpoints` with:

```json
{"url":"http://localhost:9000/webhook","event_types":["point_value_changed","alarm_raised"]}
```

3. Save the **one-time secret**. GET never returns it; delete/recreate to rotate.

| Destination policy | Rule |
|---|---|
| URLs | HTTP(S), exact allowed host; no credentials, fragments, redirects or environment proxies |
| Enforcement | Registration **and every delivery**, including migrated endpoints; removing a host blocks pending sends |
| Trust | Trust the hostname and its DNS; this is not a DNS/IP sandbox. LAN/loopback receivers are allowed |
| Event filter | Omitted or empty list selects all event types |

## Payload and signature

Headers: `Content-Type: application/json`, `X-BACnetLab-Event`, `X-BACnetLab-Signature: sha256=<hex>`.

```json
{
  "id":"<event UUID>",
  "event_type":"point_value_changed",
  "timestamp":"2026-09-13T12:00:00+00:00",
  "payload":{
    "event_type":"point_value_changed",
    "timestamp":"2026-09-13T12:00:00+00:00",
    "device_id":1001,
    "point_name":"AHU-01/CoolingValve",
    "old_value":45.0,
    "new_value":80.0
  }
}
```

| Event | Extra payload fields beyond type/time |
|---|---|
| `point_value_changed` | device_id, point_name, old_value, new_value |
| `device_status_changed` | device_id, old_status, new_status |
| `alarm_raised` | alarm_id, device_id, point_name, severity, message |
| `alarm_cleared` | alarm_id, device_id, point_name |
| `scenario_started`, `scenario_stopped`, `scenario_failed` | scenario_id, new_status, error |
| `telemetry_snapshot` | device_id, points (full point-name keys) |

Verify **raw bytes before JSON parsing**:

```python
import hashlib
import hmac


def verify(body: bytes, secret: str, header: str) -> bool:
    expected = "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header)
```

Deduplicate by event ID. Add a timestamp window compatible with retries if your receiver needs replay protection. Native changes between synchronization polls may merge; BACnet COV is independent.

## Delivery contract

```text
Event + alarm + recipients ── SQLite transaction ──► queue ──► receiver
                                                   ▲          │
                                                   └── retry ─┘
```

| Guarantee | Behaviour |
|---|---|
| Write latency | Waits for durable recording, not receiver HTTP |
| Concurrency | One worker/process; four destinations at once, one event per endpoint |
| Ordering | Later endpoint events wait behind retries; proceed after success or exhaustion |
| Success/retries | HTTP 2xx; 10s timeout; five attempts maximum, exponential delays capped at 60s |
| Durability | Pending work survives restart; crash after HTTP success can cause duplicates |
| Exhaustion | State becomes `failed`; bounded best-effort delivery, no exactly-once/guaranteed delivery |
| Inspect/test | `/api/deliveries`: state, attempts, next retry; endpoint `/test` checks connectivity, does not replay history |
| `delivered` flag | False without recipients; true only after all recipients succeed |
| Delete/retention | Endpoint deletion removes its delivery rows; old completed events/cleared alarms pruned; pending events retained |
