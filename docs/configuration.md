# Configuration

```text
defaults → config/settings.yaml → .env → process environment
                             increasing precedence ───────►
```

- Invalid settings, partial auth or empty/missing device directories fail startup.
- Packaged installs use bundled examples when no local device configuration is supplied.

| Environment variable | Default | Purpose |
|---|---|---|
| `BACNET_LAB_HTTP_HOST` | `127.0.0.1` | HTTP bind interface |
| `BACNET_LAB_HTTP_PORT` | `8080` | HTTP port |
| `BACNET_LAB_BACNET_IP` | `127.0.0.1` | Concrete IPv4 interface |
| `BACNET_LAB_BACNET_PREFIX` | `32` | IPv4 network prefix, 0–32 |
| `BACNET_LAB_BACNET_PORT_START` | `47808` | First default UDP port |
| `BACNET_LAB_DB_PATH` | `data/bacnet_lab.db` | SQLite path; Compose fixes this to `/app/data/bacnet_lab.db` |
| `BACNET_LAB_DEVICES_DIR` | `config/devices` | YAML inventory directory |
| `BACNET_LAB_LOG_LEVEL` | `INFO` | DEBUG, INFO, WARNING, ERROR or CRITICAL |
| `BACNET_LAB_SYNC_INTERVAL` | `0.25` | External value synchronization interval, seconds |
| `BACNET_LAB_SNAPSHOT_INTERVAL` | `300` | Snapshot interval, seconds |
| `BACNET_LAB_RETENTION_DAYS` | `30` | Completed event/alarm retention |
| `BACNET_LAB_AUTH_USERNAME` | empty | Basic username; configure both credentials |
| `BACNET_LAB_AUTH_PASSWORD` | empty | Basic password |
| `BACNET_LAB_WEBHOOK_ALLOWED_HOSTS` | `localhost,127.0.0.1` | Comma-separated trusted webhook hostnames/IPs |

YAML groups `http`, `bacnet`, `auth`; other keys are at the root. [Webhook URL/allowlist rules](webhooks.md#register-a-receiver).

## Network topology

For LAN use, set the actual interface address and prefix, for example:

```dotenv
BACNET_LAB_BACNET_IP=192.168.1.100
BACNET_LAB_BACNET_PREFIX=24
```

The default YAML filenames are loaded alphabetically:

| Device | ID | Default port |
|---|---|---|
| AHU-01 | 1001 | 47808 |
| CO2-01 | 5002 | 47809 |
| FCU-01 | 2001 | 47810 |
| FCU-02 | 2002 | 47811 |
| OAT-01 | 5001 | 47812 |
| TSTAT-01 | 3001 | 47813 |
| ZC-01 | 4001 | 47814 |

**Directed discovery:** send Who-Is to each address; broadcasts do not cross UDP ports.

**Shared broadcast port:** provision distinct host IPs, then set each device address:

```yaml
address:
  ip: "192.168.1.101"
  port: 47808
```

- IPs must exist on the host; the simulator does not create aliases.
- Explicit addresses keep ports stable when filenames change; duplicates are rejected.
- Allow UDP only on the intended private LAN/VPN.

## Docker

| Setting | Behaviour |
|---|---|
| Compose | 2.24+ for optional `.env` |
| Linux | Host networking |
| Development override | Bridge; publishes HTTP on host loopback; no LAN BACnet broadcast |
| Database | Named `bacnet-data` volume; survives recreation and `docker compose down` |
| Delete data | **`docker compose down -v` removes the volume** |
| File permissions | Image runs as UID 10001; custom bind mounts must be writable by that UID |
