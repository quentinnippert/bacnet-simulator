# Architecture

One async process, organized as **domain → application services → ports → adapters**. Domain code has no framework imports.

```text
BACnet client ──► BACpypes3 objects ◄── HTTP / scenarios
                 values + priorities
                         │
                   DeviceService
                         │
               SQLite + event recording
                    │            │
              API / dashboard   webhook worker
```

## State and consistency

| Rule | Behaviour |
|---|---|
| State owner | BACpypes3 owns effective values/priorities; DeviceService maintains a separate snapshot |
| Synchronization | Device API reads refresh values; background sync every 250 ms, snapshots every 300 s |
| Concurrency | Per-device locks serialize application writes, refreshes and online/offline transitions |
| Event history | Only changed effective values emit events; rapid changes between polls may merge |
| Recording failure | Propagated; the old snapshot remains so synchronization can retry |
| Atomicity | Event + recipients + alarm projection commit together; BACnet mutation and SQLite do **not** |

**After a failed write, read the effective value before retrying:** the protocol command may already have applied. Native COV is independent of the sampled event history.

## Overrides and restarts

| Operation | Preserved / restored |
|---|---|
| Override | Previous priority-8 slot, or simulated input source; other scenarios yield |
| Later external command | Preserved, even at the same value: restoration checks write revisions |
| Higher priority | Always governs the effective value |
| Device offline/reconnect | Values and priorities retained; sockets/subscriptions closed; clients must resubscribe |
| Process restart | YAML inventory/values reloaded, priorities reset, stale devices/points reconciled, old alarms cleared |
| Persistent data | Endpoints, events, alarms and pending webhook deliveries |

Stop point overrides before taking their device offline. Input `Out_Of_Service` isolates the BACnet test value from the simulated source.

## Lifecycle and maintenance

- **One Uvicorn worker.** FastAPI lifespan owns the container and all resources.
- Shutdown: scenarios → synchronization → current webhook batch (bounded wait) → device sockets → HTTP client.
- SQLite migrations are transactional/versioned; unknown future schemas fail startup.
- [Webhook worker](webhooks.md#delivery-contract): four destinations concurrently, ordered per endpoint; retention keeps pending work.
- BACpypes3 is used directly to avoid BAC0's process-global factories/tasks affecting independent devices.
- **BACpypes3 0.0.106 stays pinned.** [Compatibility table](bacnet-profile.md#bacpypes3-compatibility) records adaptations to revalidate on upgrade.

Tests cover API isolation/errors, scenarios, storage, deliveries and real UDP. HTMX/Pico assets and licenses are packaged locally.
