from pathlib import Path

import pytest

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
    with pytest.raises(ValueError, match="directory does not exist"):
        load_all_devices("nonexistent_dir")


@pytest.mark.parametrize(
    "extra",
    [
        "cov_increment: .inf",
        "cov_increment: 1.0e100",
        "cov_increment: true",
        'state_text: "off,on"',
    ],
)
def test_invalid_point_metadata_fails_at_configuration_load(tmp_path, extra):
    path = tmp_path / "bad.yaml"
    path.write_text(
        f"device_id: 1\nname: Test\npoints:\n  - object_type: analogInput\n    object_name: Temp\n    object_instance: 1\n    {extra}\n"
    )
    with pytest.raises(ValueError, match="Invalid device configuration"):
        load_device_from_yaml(path)


def test_empty_explicit_address_is_not_silently_ignored(tmp_path):
    path = tmp_path / "bad.yaml"
    path.write_text("device_id: 1\nname: Test\naddress: {}\n")
    with pytest.raises(ValueError, match="address requires"):
        load_device_from_yaml(path)
