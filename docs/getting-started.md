# Getting Started

This guide covers installing and running BACnet Lab on your machine.

## Prerequisites

- **Python 3.11+** (for local development)
- **Docker** and **Docker Compose** (for containerized deployment)

## Local Development

### Install

```bash
git clone https://github.com/YOUR_USERNAME/bacnet-lab.git
cd bacnet-lab
pip install -e ".[dev]"
```

### Run

```bash
python -m bacnet_lab
```

The application starts on http://localhost:8080. Open http://localhost:8080/ui for the web dashboard.

BACnet devices start listening on UDP ports starting at 47808 (one port per device). They are discoverable by any BACnet client on the same network.

### Run Tests

```bash
pytest
```

Tests use a `FakeNetwork` adapter — no BAC0 or BACnet network required.

## Docker (Linux)

Linux is recommended for production because `network_mode: host` is required for BACnet UDP broadcast to work across the network.

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/bacnet-lab.git
cd bacnet-lab

# Configure authentication (optional)
cp .env.example .env
# Edit .env to set BACNET_LAB_AUTH_USERNAME and BACNET_LAB_AUTH_PASSWORD

# Start
docker compose up -d --build
```

BACnet devices are fully discoverable from any machine on the same subnet.

### Stopping

```bash
docker compose down
```

### Viewing Logs

```bash
docker compose logs -f
```

## Docker (macOS/Windows)

`network_mode: host` only works on Linux. For macOS and Windows, use the development override file which switches to bridge mode with port mapping:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up --build
```

**Limitations in bridge mode:**
- BACnet devices are **not discoverable** from the host network (UDP broadcast doesn't cross Docker's virtual network)
- The REST API and web dashboard work normally on http://localhost:8080
- You can read/write BACnet points through the REST API

This is suitable for developing against the API and UI. For full BACnet network testing, use a Linux machine or VM.

## Deploy on a DigitalOcean Droplet

### 1. Create the Droplet

Create an **Ubuntu 22.04+** droplet (the $6/mo plan with 1 vCPU / 1 GB RAM is sufficient). Make sure you can SSH into it.

### 2. Install Docker

```bash
ssh root@<DROPLET_IP>

apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh

# Verify
docker --version
docker compose version
```

### 3. Configure the Firewall

```bash
ufw allow 22/tcp              # SSH
ufw allow 8080/tcp             # BACnet Lab web/API
ufw allow 47808:47815/udp      # BACnet UDP (7 devices)
ufw enable
```

### 4. Clone and Configure

```bash
cd /opt
git clone https://github.com/YOUR_USERNAME/bacnet-lab.git
cd bacnet-lab

cp .env.example .env
nano .env
```

Set a strong password in `.env`:

```
BACNET_LAB_AUTH_USERNAME=admin
BACNET_LAB_AUTH_PASSWORD=<YOUR_STRONG_PASSWORD>
```

Create the data directory for SQLite persistence:

```bash
mkdir -p data
```

### 5. Start

```bash
docker compose up -d --build
```

Verify:

```bash
docker compose logs -f
```

You should see `BACnet Lab ready on http://0.0.0.0:8080` and all 7 devices starting.

### 6. Access

Open `http://<DROPLET_IP>:8080/ui` in your browser. A login popup appears (HTTP Basic Auth). Enter the credentials from your `.env`.

Test from the command line:

```bash
curl -u admin:<YOUR_PASSWORD> http://<DROPLET_IP>:8080/api/health
```

### Updating

When you push new code to the repository:

```bash
ssh root@<DROPLET_IP>
cd /opt/bacnet-lab
git pull
docker compose up -d --build
```

### Useful Commands

| Action | Command |
|---|---|
| View logs | `docker compose logs -f` |
| Restart | `docker compose restart` |
| Stop | `docker compose down` |
| Rebuild | `docker compose up -d --build --force-recreate` |
| Change password | Edit `.env` then `docker compose restart` |

## First Steps

### 1. Open the Dashboard

Navigate to http://localhost:8080/ui. You'll see an overview of all 7 simulated devices and their current status.

### 2. Start a Scenario

Go to the Scenarios tab and start the **HVAC Day/Night Cycle**. This runs a compressed 24-hour HVAC simulation — you'll see temperatures, valve positions, and fan speeds changing in real time.

### 3. Explore the API

List all devices:

```bash
curl http://localhost:8080/api/devices
```

Get details for a specific device:

```bash
curl http://localhost:8080/api/devices/1001
```

Write a point value:

```bash
curl -X PUT http://localhost:8080/api/devices/1001/points \
  -H "Content-Type: application/json" \
  -d '{"point_name": "AHU-01/CoolingValve", "value": 80.0}'
```

### 4. Set Up a Webhook

Register an endpoint to receive real-time events:

```bash
curl -X POST http://localhost:8080/api/endpoints \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-server.com/webhook"}'
```

Save the returned `secret` — you'll need it to verify webhook signatures. See [Webhooks documentation](webhooks.md).

## What's Next

- [Devices](devices.md) — learn about the simulated devices and how to create custom ones
- [Scenarios](scenarios.md) — understand the simulation scenarios and their parameters
- [API Reference](api.md) — full REST API documentation
- [Configuration](configuration.md) — environment variables and settings
