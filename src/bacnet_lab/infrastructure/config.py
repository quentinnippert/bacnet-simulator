from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class HttpSettings:
    host: str = "0.0.0.0"
    port: int = 8080


@dataclass
class BacnetSettings:
    ip: str = "0.0.0.0"
    port_start: int = 47808


@dataclass
class AuthSettings:
    username: str = ""
    password: str = ""

    @property
    def enabled(self) -> bool:
        return bool(self.username and self.password)


@dataclass
class AppSettings:
    http: HttpSettings = field(default_factory=HttpSettings)
    bacnet: BacnetSettings = field(default_factory=BacnetSettings)
    auth: AuthSettings = field(default_factory=AuthSettings)
    db_path: str = "bacnet_lab.db"
    log_level: str = "INFO"
    devices_dir: str = "config/devices"


def load_settings(config_path: str = "config/settings.yaml") -> AppSettings:
    settings = AppSettings()
    path = Path(config_path)
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        if "http" in data:
            settings.http = HttpSettings(**data["http"])
        if "bacnet" in data:
            settings.bacnet = BacnetSettings(**data["bacnet"])
        if "db_path" in data:
            settings.db_path = data["db_path"]
        if "log_level" in data:
            settings.log_level = data["log_level"]
        if "devices_dir" in data:
            settings.devices_dir = data["devices_dir"]

    import os

    settings.http.host = os.getenv("BACNET_LAB_HTTP_HOST", settings.http.host)
    settings.http.port = int(os.getenv("BACNET_LAB_HTTP_PORT", str(settings.http.port)))
    settings.bacnet.ip = os.getenv("BACNET_LAB_BACNET_IP", settings.bacnet.ip)
    settings.bacnet.port_start = int(
        os.getenv("BACNET_LAB_BACNET_PORT_START", str(settings.bacnet.port_start))
    )
    settings.db_path = os.getenv("BACNET_LAB_DB_PATH", settings.db_path)
    settings.log_level = os.getenv("BACNET_LAB_LOG_LEVEL", settings.log_level)
    settings.auth.username = os.getenv("BACNET_LAB_AUTH_USERNAME", settings.auth.username)
    settings.auth.password = os.getenv("BACNET_LAB_AUTH_PASSWORD", settings.auth.password)

    return settings
