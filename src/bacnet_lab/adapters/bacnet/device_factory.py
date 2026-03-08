from __future__ import annotations

import logging
from pathlib import Path

import yaml

from bacnet_lab.domain.enums import PointType
from bacnet_lab.domain.models.device import Device, Point

logger = logging.getLogger(__name__)


def _parse_point(data: dict) -> Point:
    pv = data.get("present_value", 0)
    return Point(
        object_type=PointType(data["object_type"]),
        object_instance=data["object_instance"],
        object_name=data["object_name"],
        description=data.get("description", ""),
        present_value=pv,
        units=data.get("units", ""),
        cov_increment=data.get("cov_increment", 0.0),
    )


def load_device_from_yaml(path: Path) -> Device:
    with open(path) as f:
        data = yaml.safe_load(f)
    points = [_parse_point(p) for p in data.get("points", [])]
    device = Device(
        device_id=data["device_id"],
        name=data["name"],
        description=data.get("description", ""),
        points=points,
    )
    logger.info("Loaded device %s (%d) with %d points", device.name, device.device_id, len(points))
    return device


def load_all_devices(devices_dir: str) -> list[Device]:
    path = Path(devices_dir)
    if not path.exists():
        logger.warning("Devices directory %s does not exist", devices_dir)
        return []
    devices = []
    for yaml_file in sorted(path.glob("*.yaml")):
        devices.append(load_device_from_yaml(yaml_file))
    return devices
