# BACnet Lab

Simulate a small BACnet/IP network (7 devices, ~50 points) for testing and demo purposes. Deployable via Docker Compose on a Linux VM.

## Features

- **7 BACnet/IP devices** — AHU, 2 FCUs, thermostat, zone controller, outdoor temp sensor, CO2 sensor
- **~50 BACnet points** — analog inputs/outputs/values, binary I/O, multi-state values
- **Web dashboard** — real-time device monitoring with HTMX auto-refresh
- **REST API** — full CRUD for devices, scenarios, endpoints, events
- **4 simulation scenarios** — HVAC day/night cycle, alarm simulation, device offline, manual override
- **Webhook delivery** — HMAC-SHA256 signed event delivery to external systems
- **SQLite persistence** — lightweight, zero-config database

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -e ".[dev]"

# Run the application
python -m bacnet_lab
```

Open http://localhost:8080/ui for the web dashboard.

### Docker

```bash
docker compose up --build
```

> **Note**: `network_mode: host` is required for BACnet UDP broadcast. This works on Linux only. On macOS/Windows Docker Desktop, BACnet devices won't be discoverable from the host network.

## Architecture

Hexagonal architecture (ports & adapters) in a modular monolith:

```
Domain (models, events, enums)
    ↕
Ports (ABC interfaces)
    ↕
Application Services (use cases)
    ↕
Adapters (BACnet/BAC0, HTTP/FastAPI, SQLite, Webhooks)
```

## API Endpoints

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

## Devices

| Device | ID | Points | Description |
|--------|----|--------|-------------|
| AHU-01 | 1001 | 12 | Air Handling Unit |
| FCU-01 | 2001 | 7 | Fan Coil Unit Zone 1 |
| FCU-02 | 2002 | 7 | Fan Coil Unit Zone 2 |
| TSTAT-01 | 3001 | 6 | Thermostat Lobby |
| ZC-01 | 4001 | 7 | Zone Controller |
| OAT-01 | 5001 | 2 | Outdoor Temp Sensor |
| CO2-01 | 5002 | 3 | CO2 Sensor |

## Scenarios

- **HVAC Day/Night Cycle** — Compressed 24h simulation with temperature, valve, and fan variations
- **Cyclic High Temp Alarm** — Periodically raises and clears a supply air temperature alarm
- **Temporary Device Offline** — Simulates a device going offline and recovering
- **Manual Override** — Overrides a point value for a configurable duration

## Configuration

Configuration via `config/settings.yaml` or environment variables prefixed with `BACNET_LAB_`:

| Variable | Default | Description |
|----------|---------|-------------|
| `BACNET_LAB_HTTP_HOST` | `0.0.0.0` | HTTP bind address |
| `BACNET_LAB_HTTP_PORT` | `8080` | HTTP port |
| `BACNET_LAB_BACNET_IP` | `0.0.0.0` | BACnet bind IP |
| `BACNET_LAB_BACNET_PORT_START` | `47808` | First BACnet UDP port |
| `BACNET_LAB_DB_PATH` | `bacnet_lab.db` | SQLite database path |
| `BACNET_LAB_LOG_LEVEL` | `INFO` | Log level |

## Tech Stack

- Python 3.11+, BAC0 (BACpypes3), FastAPI, Uvicorn
- HTMX + Jinja2 + Pico CSS (zero JS build)
- SQLite via aiosqlite
- httpx for webhook delivery

## License

MIT
