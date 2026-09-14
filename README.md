# BACnet Simulator — Virtual HVAC Devices for BMS & SCADA Testing

**Open-source BACnet/IP simulator for developers testing BACnet clients, BMS integrations, SCADA connectors and HVAC automation without physical hardware.**

Run **7 virtual HVAC devices and 44 BACnet points** with Python or Docker. Control the simulation through a REST API and web dashboard; test discovery, reads, writes, priorities, Change of Value (COV), device availability and signed webhooks.

[Quick start](#quick-start) · [Devices](#virtual-hvac-devices) · [API reference](docs/api.md) · [BACnet capabilities](docs/bacnet-profile.md)

## Quick start

```bash
git clone https://github.com/quentinnippert/bacnet-simulator.git
cd bacnet-simulator
```

**Local development** — Python 3.11–3.13 and uv 0.12.13:

```bash
uv sync --frozen --extra dev
uv run python -m bacnet_lab
```

**Docker on Linux** — Docker Compose 2.24+:

```bash
docker compose up -d --build
```

<details>
<summary>Docker on macOS/Windows — API/UI development</summary>

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build
```

The bridge override does not provide LAN BACnet broadcast connectivity.

</details>

Open the **[dashboard](http://localhost:8080/ui)** or **[interactive API docs](http://localhost:8080/docs)**. Defaults are local-only; `.env` is optional.

> **Connecting a BACnet client:** defaults use `127.0.0.1:47808`–`47814`. Send a directed Who-Is to each address. A broadcast to one port does not discover the other ports. See [LAN and Docker networking](docs/configuration.md#network-topology).

## What you can test

| Use case | Included capabilities |
|---|---|
| **BACnet client & BMS integration** | Discovery, property reads/writes, priority arrays, relinquish, COV |
| **SCADA, building analytics & digital twins** | Virtual temperatures, valves, fans, occupancy and CO2 data |
| **HVAC automation & failure handling** | Day/night cycle, high-temperature application alarms, device offline/recovery, manual overrides |
| **Event-driven integrations** | HMAC-SHA256 webhooks, persistent queue, bounded retries and delivery history |
| **Development & CI/CD** | YAML device definitions, Docker, automated tests, optional HTTP Basic auth |

## Virtual HVAC devices

| Device | BACnet ID | Points | Equipment |
|---|---|---|---|
| AHU-01 | 1001 | 12 | Air handling unit: temperatures, valves, fans, duct pressure |
| FCU-01 / FCU-02 | 2001 / 2002 | 7 each | Fan coil units: room temperature, setpoint, occupancy |
| TSTAT-01 | 3001 | 6 | Thermostat: temperature, humidity, setpoints, operating mode |
| ZC-01 | 4001 | 7 | Zone controller: airflow, damper, reheat |
| OAT-01 | 5001 | 2 | Outdoor temperature and humidity sensor |
| CO2-01 | 5002 | 3 | CO2 sensor, setpoint and alarm point |

Analog, binary and multistate objects use real BACpypes3 protocol objects. Add devices in [`config/devices/`](config/devices/), then restart. [Full point lists and YAML example →](docs/devices.md)

## Try the REST API

With the server running, open another terminal:

```bash
# Inspect devices and their BACnet addresses
curl http://localhost:8080/api/devices

# Command a cooling valve at priority 16
curl -X PUT http://localhost:8080/api/devices/1001/points \
  -H 'Content-Type: application/json' \
  -d '{"point_name":"AHU-01/CoolingValve","value":80,"priority":16}'

# Start a compressed HVAC day/night cycle
curl -X POST http://localhost:8080/api/scenarios/hvac_day_cycle/start
```

Writes return the **effective value**: a higher priority can prevail. Send `"value":null` to release your priority slot. [API contracts →](docs/api.md)

## Development

**Stack:** Python / BACpypes3 · FastAPI · HTMX / Jinja2 / Pico CSS · SQLite · httpx. No frontend build or CDN required.

```bash
uv run pytest -q                              # Application and unit tests
BACNET_LAB_NETWORK_TESTS=1 uv run pytest -q     # Include real loopback UDP
uv run ruff check .
uv run ruff format --check .
uv build
```

- Use **one application worker**; it owns devices, scenarios and delivery processing.
- CI runs tests, including UDP, on Linux with Python 3.11–3.13.
- Contributions should include a reproducible case and relevant regression coverage.

## Documentation

| Guide | Find out how to… |
|---|---|
| [Getting started](docs/getting-started.md) | Install, explore, upgrade and back up |
| [Configuration](docs/configuration.md) | Configure LAN discovery, Docker, authentication and storage |
| [Devices](docs/devices.md) / [Scenarios](docs/scenarios.md) | Customize points and run simulations |
| [REST API](docs/api.md) / [Webhooks](docs/webhooks.md) | Integrate clients and event receivers |
| [BACnet profile](docs/bacnet-profile.md) / [Architecture](docs/architecture.md) | Understand protocol support, guarantees and compatibility code |

**Storage:** process restarts reload simulation values from YAML; webhook registrations, history and pending deliveries persist.

**Scope:** laboratory simulator; no BTL certification, native BACnet alarm notifications, routing/BBMD or BACnet/SC. Validate LAN behaviour with your target BMS. [Detailed limits →](docs/bacnet-profile.md#scope-and-verification)

[MIT License](LICENSE)
