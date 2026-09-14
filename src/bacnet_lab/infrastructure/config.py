from __future__ import annotations

import os
from ipaddress import IPv4Address
from pathlib import Path

import yaml
from dotenv import dotenv_values
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class SettingsModel(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True, allow_inf_nan=False)


class HttpSettings(SettingsModel):
    host: str = "127.0.0.1"
    port: int = Field(default=8080, ge=1, le=65535)


class BacnetSettings(SettingsModel):
    ip: str = "127.0.0.1"
    prefix: int = Field(default=32, ge=0, le=32)
    port_start: int = Field(default=47808, ge=1, le=65535)

    @field_validator("ip")
    @classmethod
    def valid_ip(cls, value: str) -> str:
        return str(IPv4Address(value))


class AuthSettings(SettingsModel):
    username: str = ""
    password: str = ""

    @model_validator(mode="after")
    def complete_credentials(self):
        if bool(self.username) != bool(self.password):
            raise ValueError("Set both auth username and password, or neither")
        if ":" in self.username:
            raise ValueError("Auth username cannot contain ':'")
        return self

    @property
    def enabled(self) -> bool:
        return bool(self.username and self.password)


class AppSettings(SettingsModel):
    http: HttpSettings = Field(default_factory=HttpSettings)
    bacnet: BacnetSettings = Field(default_factory=BacnetSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    db_path: str = "data/bacnet_lab.db"
    log_level: str = "INFO"
    devices_dir: str = Field(
        default_factory=lambda: (
            "config/devices"
            if Path("config/devices").is_dir()
            else str(Path(__file__).resolve().parents[1] / "default_config" / "devices")
        )
    )
    sync_interval: float = Field(default=0.25, gt=0, le=60)
    snapshot_interval: float = Field(default=300, gt=0)
    retention_days: int = Field(default=30, ge=1)
    webhook_allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])

    @field_validator("log_level")
    @classmethod
    def valid_level(cls, value: str) -> str:
        if value.upper() not in {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}:
            raise ValueError("Invalid log level")
        return value.upper()


def load_settings(config_path: str = "config/settings.yaml") -> AppSettings:
    path = Path(config_path)
    data = (yaml.safe_load(path.read_text()) or {}) if path.exists() else {}
    env = {**dotenv_values(".env"), **os.environ}
    for section, fields in {
        "http": ("host", "port"),
        "bacnet": ("ip", "prefix", "port_start"),
        "auth": ("username", "password"),
    }.items():
        values = dict(data.get(section, {}))
        for name in fields:
            key = f"BACNET_LAB_{section}_{name}".upper()
            if key in env:
                values[name] = env[key]
        data[section] = values
    for name in (
        "db_path",
        "log_level",
        "devices_dir",
        "sync_interval",
        "snapshot_interval",
        "retention_days",
    ):
        key = f"BACNET_LAB_{name}".upper()
        if key in env:
            data[name] = env[key]
    if "BACNET_LAB_WEBHOOK_ALLOWED_HOSTS" in env:
        data["webhook_allowed_hosts"] = [
            host.strip().lower()
            for host in env["BACNET_LAB_WEBHOOK_ALLOWED_HOSTS"].split(",")
            if host.strip()
        ]
    return AppSettings.model_validate(data)
