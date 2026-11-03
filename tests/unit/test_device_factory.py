from pathlib import Path

import pytest

from bacnet_lab.adapters.bacnet.device_factory import load_all_devices, load_device_from_yaml
from bacnet_lab.domain.enums import PointType


def test_load_device_from_yaml():
    path = Path("config/devices/ahu_01.yaml")
    device = load_device_from_yaml(path)

    assert device.device_id == 1001
    assert device.name == "AHU-01"
    assert len(device.points) == 26
    assert device.get_point_by_name("AHU-01/RoomDifferentialPressure") is None
    assert device.get_point_by_name("AHU-01/OutdoorAirHumidity") is None
    assert all(
        not any(tag in point.description for tag in ("GT81", "GM3", "GF42", "MQ41", "SO1", "P1"))
        for point in device.points
    )

    supply_temp = device.get_point_by_name("AHU-01/SupplyAirTemp")
    assert supply_temp is not None
    assert supply_temp.object_type == PointType.ANALOG_INPUT
    assert supply_temp.present_value == 22.5


def test_load_all_devices():
    devices = load_all_devices("config/devices")
    assert len(devices) == 7

    device_ids = {d.device_id for d in devices}
    assert device_ids == {1001, 2001, 2002, 3001, 4001, 5001, 5002}


def test_default_inventory_ports_without_standalone_supply_fan():
    devices = load_all_devices("config/devices")
    assert {device.name: 47808 + index for index, device in enumerate(devices)} == {
        "AHU-01": 47808,
        "CO2-01": 47809,
        "FCU-01": 47810,
        "FCU-02": 47811,
        "OAT-01": 47812,
        "TSTAT-01": 47813,
        "ZC-01": 47814,
    }


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
