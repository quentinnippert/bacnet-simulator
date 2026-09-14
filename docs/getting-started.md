# Getting started

## Install and run

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

- Open [dashboard](http://localhost:8080/ui) / [API docs](http://localhost:8080/docs).
- Defaults bind loopback. `.env` is optional; copy `.env.example` to customize.
- Configure **both** auth fields to enable Basic auth. [Network/settings reference](configuration.md).
- Startup reloads YAML inventory/values; SQLite preserves integration history and webhooks.

## First steps

1. **Devices:** inspect values; edit a commandable point. Higher priorities may prevail.
2. **Scenarios:** start HVAC Day/Night Cycle; try an alarm and inspect Events & Alarms.
3. **Webhooks:** allow your receiver's hostname, recreate the service, register it and save the secret.

## Remote access

| Access | Setup |
|---|---|
| HTTP | Loopback + HTTPS reverse proxy or SSH tunnel; configure Basic auth beyond a trusted local machine |
| BACnet UDP | Private LAN/VPN only; HTTP auth does not protect BACnet; no public UDP exposure |
| Cloud | Does not automatically join your local broadcast domain |

```bash
ssh -L 8080:127.0.0.1:8080 user@your-server
```

Then open the local dashboard URL.

## Update and preserve data

```bash
git pull
docker compose up -d --build
```

| Change | Action |
|---|---|
| `.env` | `docker compose up -d --force-recreate`; `restart` keeps the old environment |
| Normal recreation | Named database volume stays attached |
| Older installation | Back up **before** replacing the container; old DB may be `/app/bacnet_lab.db` outside the volume |

**Legacy migration:**

1. Locate the actual DB; back it up with SQLite's backup API and copy the backup out.
2. Restore as `bacnet_lab.db` in the new volume, writable by UID 10001.
3. Start the app: migration is automatic; unknown newer schemas are rejected.

Copying only a live `.db` file may omit WAL data.

## Verify / troubleshoot

```bash
uv run pytest -q
BACNET_LAB_NETWORK_TESTS=1 uv run pytest -q
uv run ruff check .
uv run ruff format --check .
uv build
docker compose config --quiet
```

| Signal | Meaning |
|---|---|
| UDP tests cannot bind | Allow loopback sockets |
| `/api/health` → 503 | Inspect returned errors |
| Fewer `online_devices` | Can be intentional during the offline scenario |
| Missing webhook | Inspect `/api/deliveries` for pending/retrying/failed work |
