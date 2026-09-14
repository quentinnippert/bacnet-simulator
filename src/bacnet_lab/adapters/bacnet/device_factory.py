from __future__ import annotations

from ipaddress import IPv4Address
from pathlib import Path

import yaml

from bacnet_lab.domain.models.device import Device, Point
from bacnet_lab.domain.value_objects import DeviceAddress


def load_device_from_yaml(path: Path) -> Device:
    try:
        data = yaml.safe_load(path.read_text())
        if not isinstance(data, dict):
            raise ValueError("Expected a device mapping")
        data = dict(data)
        points = [Point(**point) for point in data.pop("points", [])]
        address = data.pop("address", None)
        if address is not None:
            if (
                not isinstance(address, dict)
                or set(address) != {"ip", "port"}
                or type(address["port"]) is not int
                or not 1 <= address["port"] <= 65535
            ):
                raise ValueError("address requires an IPv4 ip and port in 1..65535")
            address = DeviceAddress(str(IPv4Address(address["ip"])), address["port"])
        return Device(**data, points=points, address=address)
    except (TypeError, ValueError, KeyError, yaml.YAMLError) as exc:
        raise ValueError(f"Invalid device configuration {path}: {exc}") from exc


def load_all_devices(devices_dir: str) -> list[Device]:
    path = Path(devices_dir)
    if not path.is_dir():
        raise ValueError(f"Devices directory does not exist: {devices_dir}")
    devices = [load_device_from_yaml(p) for p in sorted(path.glob("*.yaml"))]
    if not devices:
        raise ValueError(f"No devices found in {devices_dir}")
    if len({d.device_id for d in devices}) != len(devices) or len({d.name for d in devices}) != len(
        devices
    ):
        raise ValueError("Device IDs and names must be unique")
    addresses = [str(d.address) for d in devices if d.address]
    if len(set(addresses)) != len(addresses):
        raise ValueError("Device addresses must be unique")
    return devices
