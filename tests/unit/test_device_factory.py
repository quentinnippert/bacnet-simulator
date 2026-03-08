from pathlib import Path

from bacnet_lab.adapters.bacnet.device_factory import load_all_devices, load_device_from_yaml
from bacnet_lab.domain.enums import PointType


def test_load_device_from_yaml():
    path = Path("config/devices/ahu_01.yaml")
    device = load_device_from_yaml(path)

    assert device.device_id == 1001
    assert device.name == "AHU-01"
    assert len(device.points) == 12

    supply_temp = device.get_point_by_name("AHU-01/SupplyAirTemp")
    assert supply_temp is not None
    assert supply_temp.object_type == PointType.ANALOG_INPUT
    assert supply_temp.present_value == 22.5


def test_load_all_devices():
    devices = load_all_devices("config/devices")
    assert len(devices) == 7

    device_ids = {d.device_id for d in devices}
    assert device_ids == {1001, 2001, 2002, 3001, 4001, 5001, 5002}


def test_load_all_devices_missing_dir():
    devices = load_all_devices("nonexistent_dir")
    assert devices == []
