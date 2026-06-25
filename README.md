# BACnet Simulator

**Open-source BACnet/IP simulator for developers testing BACnet clients, BMS integrations, SCADA connectors, and HVAC automation software without physical devices.**

Run a realistic BACnet test network in seconds with Docker: 7 virtual HVAC devices, ~50 BACnet points, REST API control, web dashboard, scenarios, alarms, and webhooks.

Use it to:

- test BACnet discovery, reads, writes, and device availability
- simulate HVAC equipment such as AHUs, FCUs, thermostats, zone controllers, CO2 sensors, and outdoor temperature sensors
- build and validate BMS, SCADA, building analytics, or digital twin integrations
- run repeatable BACnet integration tests in development or CI/CD

## Who is this for?

BACnet Simulator is built for developers working on:

- BACnet client libraries
- BMS / Building Management System integrations
- SCADA connectors
- building analytics platforms
- HVAC automation software
- digital twin platforms for buildings
- industrial IoT gateways
- CI/CD tests requiring virtual BACnet/IP devices

## Features

| Feature | Description |
|---------|-------------|
| **7 Virtual BACnet/IP Devices** | AHU, 2 FCUs, thermostat, zone controller, outdoor temp sensor, CO2 sensor |
| **~50 BACnet Points** | Analog inputs/outputs/values, binary I/O, multi-state values |
| **REST API** | Full CRUD for devices, scenarios, webhook endpoints, events |
| **Web Dashboard** | Real-time monitoring with HTMX auto-refresh (zero JS build) |
| **4 Simulation Scenarios** | HVAC day/night cycle, alarm simulation, device offline, manual override |
| **Webhook Events** | HMAC-SHA256 signed delivery to external systems |
| **Docker Compose** | One-command deployment on Linux with `network_mode: host` |
| **SQLite Persistence** | Zero-configuration database |
| **HTTP Basic Auth** | Optional authentication via environment variables |

## Quick Start

### Docker (recommended)

```bash
git clone https://github.com/quentinnippert/bacnet-simulator.git
cd bacnet-simulator
docker compose up -d --build
```

Open http://localhost:8080/ui for the web dashboard.

> **Note:** `network_mode: host` is required for BACnet UDP broadcast and only works on Linux. For macOS/Windows development, see the [Getting Started guide](docs/getting-started.md#docker-macoswindows).

### Local Development

```bash
pip install -e ".[dev]"
python -m bacnet_lab
```

See the full [Getting Started guide](docs/getting-started.md) for detailed instructions.

## Simulated Devices

| Device | ID | Points | Description |
|--------|----|--------|-------------|
| AHU-01 | 1001 | 12 | Air Handling Unit — supply/return/mixed air temps, valves, fans, pressure |
| FCU-01 | 2001 | 7 | Fan Coil Unit Zone 1 — room temp, valve, fan speed |
| FCU-02 | 2002 | 7 | Fan Coil Unit Zone 2 — room temp, valve, fan speed |
| TSTAT-01 | 3001 | 6 | Thermostat Lobby — temp, setpoints, occupancy |
| ZC-01 | 4001 | 7 | Zone Controller — damper, airflow, CO2, occupancy |
| OAT-01 | 5001 | 2 | Outdoor Temperature Sensor |
| CO2-01 | 5002 | 3 | CO2 Sensor |

Each device runs on a dedicated UDP port and is fully discoverable on the BACnet network. Device definitions are YAML files in `config/devices/` — easy to add or modify.

See [Devices documentation](docs/devices.md) for full point lists and custom device creation.

## Simulation Scenarios

| Scenario | Description |
|----------|-------------|
| **HVAC Day/Night Cycle** | Compressed 24h simulation — outdoor temp varies, valves/fans respond, occupancy changes |
| **Cyclic High Temp Alarm** | Periodically raises and clears a supply air temperature alarm |
| **Device Offline** | Simulates a device going offline and recovering |
| **Manual Override** | Overrides a point value for a configurable duration |

Start/stop scenarios via the REST API or web dashboard. See [Scenarios documentation](docs/scenarios.md).

## REST API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/devices` | List all devices |
| GET | `/api/devices/{id}` | Device details with points |
| PUT | `/api/devices/{id}/points` | Write a point value |
| GET | `/api/scenarios` | List scenarios |
| POST | `/api/scenarios/{id}/start` | Start a scenario |
| POST | `/api/scenarios/{id}/stop` | Stop a scenario |
| GET | `/api/endpoints` | List webhook endpoints |
| POST | `/api/endpoints` | Create webhook endpoint |
| DELETE | `/api/endpoints/{id}` | Delete endpoint |
| POST | `/api/endpoints/{id}/test` | Test webhook delivery |
| GET | `/api/events` | Recent events |
| GET | `/api/alarms` | Recent alarms |

See the full [API Reference](docs/api.md) for request/response examples.

## Use Cases

- **BMS integration testing** — validate your Building Management System against realistic BACnet devices
- **SCADA development** — build and test SCADA connectors without physical hardware
- **BACnet client testing** — verify your BACnet client handles discovery, reads, writes, and COV correctly
- **Building analytics prototyping** — develop analytics on realistic HVAC data streams
- **CI/CD pipelines** — spin up a BACnet network in your test environment
- **Training and demos** — demonstrate HVAC automation behavior without physical equipment
- **Webhook integration testing** — verify your event handlers with real BACnet events

## Architecture

Hexagonal architecture (ports & adapters) for clean testability and extensibility:

```
Domain (models, events, enums)
    |
Ports (abstract interfaces)
    |
Application Services (use cases)
    |
Adapters (BACnet/BAC0, HTTP/FastAPI, SQLite, Webhooks)
```

See [Architecture documentation](docs/architecture.md) for details.

## Tech Stack

- **Python 3.11+** with async/await throughout
- **BAC0** (BACpypes3) — BACnet/IP protocol stack
- **FastAPI** + Uvicorn — REST API
- **HTMX** + Jinja2 + Pico CSS — web dashboard (zero JS build)
- **SQLite** via aiosqlite — persistence
- **httpx** — async webhook delivery

## Documentation

| Document | Description |
|----------|-------------|
| [Getting Started](docs/getting-started.md) | Installation, deployment, first steps |
| [Devices](docs/devices.md) | Simulated devices, points, custom device creation |
| [Scenarios](docs/scenarios.md) | Simulation scenarios and parameters |
| [API Reference](docs/api.md) | REST API with request/response examples |
| [Webhooks](docs/webhooks.md) | Event delivery, signatures, payload examples |
| [Configuration](docs/configuration.md) | Settings, environment variables, authentication |
| [Architecture](docs/architecture.md) | Project structure and design decisions |

## Contributing

Contributions are welcome. Please open an issue to discuss your idea before submitting a PR.

## License

MIT
